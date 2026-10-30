# -*- coding: utf-8 -*-
"""Agent 执行循环（阶段4，提示词7）：自研轻量 Harness。

选型说明（为什么不用 LangChain 等重框架）：
- 确认门与决策日志需要完全掌控循环细节（中断、落库时机），重框架反而难插桩；
- 零新增依赖，与现有 llm_gateway / retrieval_service 无缝衔接；
- 循环本体不足百行，可读可测，阶段5 评测可直接复用日志表分析。

执行模型（最多 5 轮，防工具死循环）：
    ┌──────────────────────────────────────────────┐
    │ 1) complete_llm(消息, 5个工具) → 模型决策      │
    │ 2a) 决策=tool_calls → execute_tool → 结果回填  │──┐
    │     ├─ create 申请成功 → 确认门中断（发确认事件）│  │ 回到 1
    │     └─ 其他工具 → 继续                         │◄─┘
    │ 2b) 决策=直答 → 流式输出最终回答，结束          │
    └──────────────────────────────────────────────┘
    超过 5 轮 → 兜底：退回 RAG 直答（阶段2/3 行为），保证任何问题都有回答。

SSE 事件协议（阶段4 扩展，前端 static/index.html 同步支持）：
    status(thinking) → tool(×N) → [confirm_required] → message(×N)
    → citations → done {tools_used}
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from ..schemas import ApiError
from .llm_gateway import complete_llm, sanitize_for_llm, stream_llm
from .prompt_assembler import build_messages
from .tools import ToolContext, execute_tool, get_tool_schemas
from .tools.registry import log_decision

# Agent 最大轮次（一轮 = 一次决策；超出后兜底直答）
MAX_ROUNDS = 5

# 工具中文名（SSE tool 事件展示用）
TOOL_LABELS = {
    "query_course_schedule": "查询课表",
    "search_selection_rules": "检索选课制度",
    "check_course_requirements": "查询课程要求",
    "validate_eligibility": "校验选课资格",
    "create_selection_application": "生成选课申请",
}


def _sse(event: str, data: dict | list) -> dict:
    """包装成 sse-starlette 需要的 {event, data(json字符串)} 结构。"""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _split_stream(text: str, size: int = 24) -> list[str]:
    """把完整回答切块（模拟流式；前端打字机负责渲染节奏）。"""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def run_agent_loop(conv_id: int, question: str, hits: list[dict[str, Any]],
                         history: list[dict[str, str]], system_prompt: str,
                         ctx: ToolContext, result_box: dict[str, Any]
                         ) -> AsyncIterator[dict]:
    """执行 Agent 循环，yield SSE 事件；最终回答写入 result_box。

    result_box 约定（chat_service 落库时读取）：
        answer       最终回答全文（str）
        citations    引用来源列表（普通直答路径 = RAG hits）
        application  create 成功的申请单 dict（confirm_required 已发送）
        tools_used   实际调用过的工具名列表（done 事件 / 评测分析）
    """
    # Agent 路径消息：系统提示词（含工具约束） + 历史 + 脱敏问题。
    # 注意不预置 RAG 上下文 —— 制度依据由模型按需调 search_selection_rules 获取。
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": f"【学生问题】\n{sanitize_for_llm(question)}"},
    ]
    tools_schema = get_tool_schemas()
    result_box.setdefault("citations", [])
    result_box["tools_used"] = []
    # 防重复调用保护：同一请求内 (工具名, 参数) 完全相同的调用只执行一次，
    # 重复请求直接回填错误说明（真实 LLM 也可能出现重复决策，实测防御）
    seen_calls: set[tuple[str, str]] = set()

    for round_no in range(1, MAX_ROUNDS + 1):
        # ── 1) 模型决策（非流式；异常 → SSE error 事件，流内不静默失败）──
        try:
            decision = await complete_llm(messages, tools=tools_schema)
        except ApiError as exc:
            yield _sse("error", {"code": exc.code, "message": exc.message})
            result_box["answer"] = ""
            return

        calls = decision.get("tool_calls")

        # ── 2b) 直答分支 ──
        if not calls:
            content = decision.get("content")
            if content:
                # 模型已给出完整回答（mock 拼装 / 真实供应商非流式返回）→ 切块回放
                result_box["answer"] = content
                for piece in _split_stream(content):
                    yield _sse("message", {"delta": piece})
            else:
                # 无工具意图 → RAG 直答回退（与阶段2/3 完全一致的行为）
                citations = [
                    {"index": i, "source": h["meta"]["source"],
                     "heading": h["meta"]["heading"],
                     "chunk_no": h["meta"]["chunk_no"],
                     "preview": h["meta"]["content"][:60]}
                    for i, h in enumerate(hits, start=1)
                ]
                result_box["citations"] = citations
                pieces: list[str] = []
                try:
                    async for delta in stream_llm(
                            build_messages(question, hits, history, system_prompt)):
                        pieces.append(delta)
                        yield _sse("message", {"delta": delta})
                except ApiError as exc:
                    yield _sse("error", {"code": exc.code, "message": exc.message})
                    result_box["answer"] = ""
                    return
                result_box["answer"] = "".join(pieces)

            # 最终作答也记一条决策日志（阶段5 分析完整轨迹）
            await log_decision(conv_id, round_no, "__final_answer__",
                               {"question": question[:60]}, 0,
                               (result_box["answer"] or "")[:200])
            return

        # ── 2a) 工具调用分支：回填 assistant(tool_calls) 消息 ──
        messages.append({
            "role": "assistant", "content": decision.get("content"),
            "tool_calls": [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"],
                              "arguments": json.dumps(c["arguments"], ensure_ascii=False)}}
                for c in calls
            ],
        })

        for call in calls:
            name, args = call["name"], call["arguments"]
            # tool 事件（前端展示"正在查询课表…"步骤条）
            yield _sse("tool", {"round": round_no, "name": name,
                                "label": TOOL_LABELS.get(name, name),
                                "arguments": args, "phase": "start"})

            call_key = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
            if call_key in seen_calls:
                result = {"error": "重复调用相同工具与参数（本次对话已执行过），"
                                   "请勿重复调用，请基于已有结果回答"}
            else:
                seen_calls.add(call_key)
                result = await execute_tool(ctx, round_no, name, args)

            yield _sse("tool", {"round": round_no, "name": name,
                                "label": TOOL_LABELS.get(name, name),
                                "arguments": args, "phase": "done",
                                "ok": "error" not in result,
                                "summary": _brief(result)})
            result_box["tools_used"].append(name)

            # 工具结果回填（OpenAI tool 协议）
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False)})

            # ── 确认门：create 成功 → 强制中断循环，发确认卡片 ──
            if name == "create_selection_application" and result.get("created"):
                result_box["application"] = result
                closing = (f"选课申请已生成（业务编号 {result['business_no']}）。"
                           f"系统不代替你选课：请在下方确认卡片中点击【确认提交】，"
                           f"申请将提交教务管理员审核（制度 2.7）。")
                result_box["answer"] = closing
                for piece in _split_stream(closing):
                    yield _sse("message", {"delta": piece})
                yield _sse("confirm_required", {
                    "business_no": result["business_no"],
                    "application": _application_view(result),
                })
                # 确认门中断也记一条决策日志（评测轨迹完整性）
                await log_decision(conv_id, round_no, "__confirm_gate__",
                                   {"business_no": result["business_no"]}, 0,
                                   f"申请单已生成，等待学生确认")
                return

    # ── 兜底：超过最大轮次 → RAG 直答（任何问题都不能没有回答）──
    fallback = ("（已达到单次对话的最大工具调用轮次，改为直接依据制度条文回答。）")
    pieces = [fallback]
    yield _sse("message", {"delta": fallback})
    citations = [
        {"index": i, "source": h["meta"]["source"], "heading": h["meta"]["heading"],
         "chunk_no": h["meta"]["chunk_no"], "preview": h["meta"]["content"][:60]}
        for i, h in enumerate(hits, start=1)
    ]
    result_box["citations"] = citations
    try:
        async for delta in stream_llm(
                build_messages(question, hits, history, system_prompt)):
            pieces.append(delta)
            yield _sse("message", {"delta": delta})
    except ApiError as exc:
        yield _sse("error", {"code": exc.code, "message": exc.message})
        result_box["answer"] = ""
        return
    result_box["answer"] = "".join(pieces)
    await log_decision(conv_id, MAX_ROUNDS, "__fallback_answer__",
                       {"question": question[:60]}, 0, result_box["answer"][:200])


def _brief(result: dict[str, Any]) -> str:
    """工具结果的一句话摘要（SSE tool 事件展示；脱敏后的业务口径）。"""
    if "error" in result:
        return f"执行出错：{result['error']}"
    if "schedule" in result:
        return f"《{result.get('course_name')}》{result.get('semester')} 排课已获取"
    if "rules" in result:
        return f"检索到 {len(result['rules'])} 条制度条文"
    if "course_type" in result:
        return (f"《{result.get('course_name')}》：{result.get('course_type')}，"
                f"{result.get('credits')} 学分")
    if "eligible" in result:
        return (f"《{result.get('course_name')}》资格校验："
                f"{'通过' if result.get('eligible') else '不符'}")
    if "created" in result:
        return (f"申请单 {result.get('business_no')} 已生成（draft）"
                if result.get("created") else f"创建被拦截：{result.get('message', '')[:60]}")
    return "已执行"


def _application_view(app: dict[str, Any]) -> dict[str, Any]:
    """确认卡片与审核页共用的申请单视图（前端展示结构）。"""
    course, student = app["course"], app["student"]
    eligibility = app.get("eligibility", {})
    return {
        "business_no": app["business_no"],
        "status": app["status"],
        "student": student,
        "semester": app["semester"],
        "course": course,
        "eligibility": {
            "eligible": eligibility.get("eligible"),
            "checks": [{"item": c["item"], "passed": c["passed"],
                        "detail": c["detail"], "rule": c["rule"]}
                       for c in eligibility.get("checks", [])],
        },
        "rule_refs": app.get("rule_refs", []),
        "confirm_hint": app.get("confirm_hint", ""),
    }
