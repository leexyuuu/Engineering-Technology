# -*- coding: utf-8 -*-
"""工具注册表（阶段4，提示词7）：5 个工具的统一登记、Schema 定义与执行分发。

OpenAI Function Calling 协议格式（真实供应商可直接使用；mock 供应商按
同一 schema 做脚本化决策）。接其他供应商（如 Anthropic）时只需在此处
适配 schema 转换，工具实现零改动。

调用顺序约束（双层防护的"提示词层"写在系统提示词里，见 prompt_assembler；
"代码层"硬约束见 eligibility_tools.create_selection_application）：
    1. query_course_schedule        课表查询（只读）
    2. search_selection_rules       制度规则检索（只读，RAG）
    3. check_course_requirements    课程要求查询（只读）
    4. validate_eligibility         选课资格校验（只读，规则引擎）
    5. create_selection_application 创建选课申请（受控写入，仅学生确认后）
"""
from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable

from ...db import AsyncSessionLocal
from ...models import AgentDecisionLog
from .context import ToolContext
from .course_tools import check_course_requirements, query_course_schedule
from .eligibility_tools import create_selection_application, validate_eligibility
from .rule_tools import search_selection_rules

# 工具处理器签名：(ctx, arguments) -> 结果字典
ToolHandler = Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "query_course_schedule": query_course_schedule,
    "search_selection_rules": search_selection_rules,
    "check_course_requirements": check_course_requirements,
    "validate_eligibility": validate_eligibility,
    "create_selection_application": create_selection_application,
}

# OpenAI Function Calling 的工具描述（模型据此决定何时调用哪个工具）
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_course_schedule",
            "description": "查询指定课程在目标学期的排课信息（星期、节次、教室、"
                           "教师、课表版本）。适用：'XX课周几上课'、'XX课在哪个"
                           "教室'等课表问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name_or_code": {
                        "type": "string",
                        "description": "课程名称或课程代码，如'数据结构'或'CS201'"},
                },
                "required": ["course_name_or_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_selection_rules",
            "description": "检索教务管理制度条文（选课规则/排课规则/学分标准/调课"
                           "规定）。适用：学生询问制度依据时调用，回答必须引用检索"
                           "到的条文。规则类问题（如学分上限、时间冲突如何处理、"
                           "毕业学分、选课时间）应先检索并直接依据条文作答，不要反问"
                           "具体课程名称。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要检索的制度问题关键词，如'选课时间安排'"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_course_requirements",
            "description": "查询课程要求：课程类型（必修/选修）、学分、学时、先修课、"
                           "容量。学生表达选课意向后，先调用本工具了解课程要求。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name_or_code": {
                        "type": "string",
                        "description": "课程名称或课程代码"},
                },
                "required": ["course_name_or_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_eligibility",
            "description": "校验学生选修指定课程的资格（先修课/时间冲突/学分上限/"
                           "容量，逐项给出结论与制度依据）。创建选课申请前【必须】"
                           "先调用本工具且校验通过。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name_or_code": {
                        "type": "string",
                        "description": "课程名称或课程代码"},
                },
                "required": ["course_name_or_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_selection_application",
            "description": "为学生创建选课申请单（draft 草稿，待学生本人确认后再"
                           "提交教务审核）。前置条件：本会话内 validate_eligibility "
                           "已对该课程校验通过，否则会被安全策略拦截。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name_or_code": {
                        "type": "string",
                        "description": "课程名称或课程代码"},
                },
                "required": ["course_name_or_code"],
            },
        },
    },
]


def get_tool_schemas() -> list[dict[str, Any]]:
    """返回工具 Schema 列表（传给 LLM 的 tools 参数）。"""
    return TOOL_SCHEMAS


def _summarize(result: Any, limit: int = 300) -> str:
    """把工具结果压成一行摘要（决策日志展示用，避免日志表膨胀）。"""
    try:
        text = json.dumps(result, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(result)
    return text[:limit] + ("…" if len(text) > limit else "")


async def log_decision(conversation_id: int, round_no: int, tool_name: str,
                       params: dict | None, duration_ms: int, summary: str) -> None:
    """写一条 Agent 决策日志（阶段5 评测分析的数据基础；agent_loop 也用于最终作答轮）。"""
    async with AsyncSessionLocal() as db:
        db.add(AgentDecisionLog(
            conversation_id=conversation_id, round=round_no, tool_name=tool_name,
            params=params, duration_ms=duration_ms, result_summary=summary))
        await db.commit()


async def execute_tool(ctx: ToolContext, round_no: int, name: str,
                       arguments: dict[str, Any]) -> dict[str, Any]:
    """执行一个工具并记录决策日志；未知工具/执行异常返回结构化错误（不抛出）。

    返回值约定（喂回 LLM 的 tool 消息 content）：
        正常 → 工具自身的结构化结果；
        异常 → {"error": "…"}，由模型决定向学生的解释话术。
    """
    handler = TOOL_HANDLERS.get(name)
    t0 = time.perf_counter()
    if handler is None:
        result = {"error": f"未知工具：{name}"}
    else:
        try:
            result = await handler(ctx, arguments)
        except Exception as exc:   # noqa: BLE001 —— 工具故障不拖垮整个对话
            result = {"error": f"工具执行异常：{exc}"}
    duration_ms = int((time.perf_counter() - t0) * 1000)

    await log_decision(ctx.conversation_id, round_no, name, arguments,
                       duration_ms, _summarize(result))
    return result
