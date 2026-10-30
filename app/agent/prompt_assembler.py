# -*- coding: utf-8 -*-
"""提示词装配（阶段4 升级）：系统提示词 + 最近 6 轮历史 + 编号制度条文 + 学生问题。

阶段4 变化（提示词7）：
- DEFAULT_SYSTEM_PROMPT 升级为 Agent 版：加入工具使用顺序约束与禁令
  （提示词层软约束；代码层硬约束见 eligibility_tools，双层防护）；
- LEGACY_DEFAULT_PROMPTS 保留历史版本默认值：启动时检测数据库模板仍是
  旧默认（未被管理员自定义编辑）→ 平滑升级为新默认，不覆盖自定义内容；
- build_messages 保持不变：普通制度问答（无需工具路径）继续走
  "RAG 检索 → 编号条文 → 直答"，与阶段 2/3 行为完全兼容。
"""
from __future__ import annotations

from typing import Any

from .llm_gateway import sanitize_for_llm

# ── Agent 版默认系统提示词（首次启动写入数据库；此后以数据库编辑版为准）──
DEFAULT_SYSTEM_PROMPT = (
    "你是知行职业学院的教务制度与选课助手，服务对象是学生。\n"
    "【回答原则】只依据制度条文与工具返回的课表/课程/资格数据回答，不确定时明确"
    "说'制度中未找到'，回答末尾附引用来源（制度条文编号或课表版本），不得编造。\n"
    "【工具使用顺序】学生需要选课时按序执行：1) search_selection_rules 查选课制度；"
    "2) check_course_requirements 查课程要求；3) 向学生复述课程信息并请其确认选课"
    "意向；4) validate_eligibility 校验资格；5) 校验通过后 create_selection_application"
    " 创建申请（系统会发确认卡片，学生本人确认后才提交教务审核）。\n"
    "【安全禁令】禁止跳过 validate_eligibility 直接创建选课申请（会被系统拦截）；"
    "禁止代替学生确认；仅受理学生本人的选课请求，禁止代他人办理；资格不符时如实"
    "告知原因，并提示可按制度 2.6 走特殊申请（须教务管理员确认）；系统接口只读，"
    "不代替学生选课、不修改成绩（制度 2.7）。\n"
    "【数据时效】课表数据每 15 分钟同步一次，引用时提示'以教务系统最终数据为准'。"
)

# ── 历史版本默认提示词（阶段2/3）：用于识别"未被自定义编辑"的旧模板并平滑升级 ──
LEGACY_DEFAULT_PROMPTS: list[str] = [
    "你是学校教务制度助手，只根据提供的制度条文回答，不确定时明确说'制度中未找到'，"
    "回答末尾附引用来源，不得编造排课或选课规则。",
]


def build_messages(question: str, hits: list[dict[str, Any]],
                   history: list[dict[str, str]] | None = None,
                   system_prompt: str | None = None) -> list[dict[str, str]]:
    """装配普通制度问答的 LLM 消息列表（无需工具路径，OpenAI 消息格式）。

    - history：最近 6 轮（12 条）历史消息，[{role, content}]，时间正序；
    - 当前问题附带检索到的制度条文（编号与引用对应）；
    - 问题先出校脱敏再进入提示词（Q6）。
    """
    blocks = []
    for i, h in enumerate(hits, start=1):
        meta = h["meta"]
        blocks.append(
            f"[{i}] 来源：{meta['source']} · {meta['heading']}（片段#{meta['chunk_no']}）\n{meta['content']}")
    context = "\n\n".join(blocks)

    user_msg = f"【制度条文检索结果】\n{context}\n\n【学生问题】\n{sanitize_for_llm(question)}"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
    ]
    messages.extend(history or [])                       # 多轮上下文（代词指代、追问）
    messages.append({"role": "user", "content": user_msg})
    return messages
