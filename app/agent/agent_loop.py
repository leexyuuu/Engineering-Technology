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
import re
from typing import Any, AsyncIterator

from sqlalchemy import select

from ..db import AsyncSessionLocal
from ..models import AgentDecisionLog
from ..schemas import ApiError
from .llm_gateway import complete_llm, sanitize_for_llm, stream_llm
from .prompt_assembler import build_messages, with_course_catalog
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


# 安全拒答/引导话术标记：命中即视为"可接受的无工具直答"，不强制改走 RAG
_SAFE_ANSWER_MARKERS = ("抱歉", "不能", "无法", "不可", "不便", "不提供", "不受理",
                        "请提供", "请告诉我", "请咨询", "建议咨询", "未找到", "请稍后",
                        "不代替", "不修改", "不编造")


def _looks_ungrounded(answer: str) -> bool:
    """无工具直答时判断答案是否属于"未检索就作答"（需强制回退 RAG）。

    安全拒答、超范围说明、引导话术不强制检索（这类回答不需要制度事实支撑）。
    """
    return not any(k in answer for k in _SAFE_ANSWER_MARKERS)


# ── 安全硬约束（提示词9 评测 V01/V04 暴露的真实供应商问题）──
# 提示词层已写禁令，但真实模型仍可能跳过审核直接建申请（V01）、
# 或回显他人姓名（V04）；此处做代码层确定性拦截：命中即标准化拒答，
# 完全不进入工具循环（不产生任何写入、确认卡片与他人信息）。
_BYPASS_AUDIT_PATTERN = re.compile(
    r"(不用|无需|不必|免|跳过|绕过|省去).{0,4}(审核|审批)"
    r"|直接.{0,4}(加进|加入).{0,4}课表")
_THIRD_PARTY_PATTERN = re.compile(
    r"(同学|室友|朋友|别人|他人|同事|学长|学姐).{0,6}(课表|成绩|选课|个人信息|联系方式)")
# 诱导修改制度参数（学分上限等）：只读系统，须明确拒绝并给出制度规定值（2.4）
_RULE_TAMPER_PATTERN = re.compile(
    r"学分.{0,4}上限|上限.{0,4}(学分|调到|改成)|(调|改).{0,4}\d+\s*学分")

# 学生已确认选课的标志（上一轮助手的确认话术）；没有它不得创建申请（M01 评测暴露）
# 真实供应商措辞多样（"确认是否选课""请确认""请您确认…"），此处覆盖倒序/敬语变体
_CONFIRM_ASK_PATTERN = re.compile(
    r"确认要选|是否确认|确认是否|确认选|请确认|请您确认|请你确认|是否要选|回复.{0,2}确认")

# 学生本人的确认语：整句即确认（"确认，顺便…"这类混合请求不算，避免夹带越权意图）
_CONFIRM_REPLY_PATTERN = re.compile(
    r"^\s*(确认|确定|好的|可以|同意|没问题|是|是的|行|ok)\s*[！!。，,.]?\s*$", re.I)

# 呈现过选课信息的工具（查课程要求 / 校验资格）：作为状态化确认门的"意向已呈现"证据
_INTENT_TOOLS = ("check_course_requirements", "validate_eligibility")

_BYPASS_REFUSAL = (
    "抱歉，选课必须走「提交申请 → 你本人确认 → 教务管理员审核」流程（制度 2.7），"
    "系统不代替你选课，也不能跳过审核把课程直接放进课表。\n"
    "如果你需要选这门课，我可以先帮你查课程要求、校验资格，再生成需要你本人确认的"
    "选课申请单，由教务管理员审核后生效。")

_THIRD_PARTY_REFUSAL = (
    "抱歉，我只能查询你本人的课表、成绩与选课信息，不能提供他人的个人信息。"
    "如果你需要查询自己的课表，请告诉我你自己的课程名称或课程代码。")

_RULE_TAMPER_REFUSAL = (
    "抱歉，每学期选课学分上限由教务制度规定（制度 2.4：每学期选课总学分须在 16–28 "
    "学分之间，上限 28 学分），系统只读（制度 2.7），我不能修改制度参数。\n"
    "如确有特殊原因需要超出上限，可按制度 2.6 提交特殊申请，由教务管理员审核确认。")


def _safety_refusal(question: str) -> str | None:
    """命中越权/违规意图时返回标准化拒答话术，否则返回 None。"""
    if _BYPASS_AUDIT_PATTERN.search(question):
        return _BYPASS_REFUSAL
    if _RULE_TAMPER_PATTERN.search(question):
        return _RULE_TAMPER_REFUSAL
    if _THIRD_PARTY_PATTERN.search(question):
        return _THIRD_PARTY_REFUSAL
    return None


def _asked_confirmation(messages: list[dict[str, Any]]) -> bool:
    """是否已在对话中向学生复述课程信息并请其确认（创建申请的前置条件）。"""
    return any(m.get("role") == "assistant" and m.get("content")
               and _CONFIRM_ASK_PATTERN.search(m["content"]) for m in messages)


def _prior_turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """当前问题之前的历史消息（当前轮之后新追加的工具证据不参与判定）。"""
    last_user = 0
    for i, m in enumerate(messages):
        if m.get("role") == "user":
            last_user = i
    return messages[:last_user]


def _presented_selection(messages: list[dict[str, Any]]) -> bool:
    """历史中是否已查过课程要求/资格（即已向学生呈现过选课信息）。"""
    for m in messages:
        for c in m.get("tool_calls") or []:
            if (c.get("function") or {}).get("name") in _INTENT_TOOLS:
                return True
    return False


def _may_create_application(conv_id: int, messages: list[dict[str, Any]],
                            question: str) -> bool:
    """状态化确认门（同步部分）：历史已呈现选课信息 + 学生本轮确认。

    历史消息从库中只带 role/content，跨轮工具证据需用 _has_prior_intent 查库，
    因此真正调用见 _check_confirm_gate。
    """
    prior = _prior_turns(messages)
    if not _presented_selection(prior):
        return False
    return bool(_CONFIRM_REPLY_PATTERN.match(question)) or _asked_confirmation(prior)


async def _has_prior_intent(conv_id: int) -> bool:
    """会话历史中是否已查过课程要求/资格（状态化确认门的"意向已呈现"证据）。

    走 AgentDecisionLog（每次工具执行都会落库），不依赖助手具体措辞。
    """
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(AgentDecisionLog.id)
            .where(AgentDecisionLog.conversation_id == conv_id,
                   AgentDecisionLog.tool_name.in_(_INTENT_TOOLS))
            .limit(1))).first()
    return row is not None


async def _check_confirm_gate(conv_id: int, messages: list[dict[str, Any]],
                              question: str) -> bool:
    """确认门判定：已呈现选课信息（会话历史或库中决策日志）且学生本轮确认。

    仅靠正则匹配助手话术会漏判（M01/M05 评测暴露），故以会话状态为主判据。
    """
    if _may_create_application(conv_id, messages, question):
        return True
    return await _has_prior_intent(conv_id) and (
        bool(_CONFIRM_REPLY_PATTERN.match(question)) or _asked_confirmation(messages))


_SPECIAL_APPROVAL_HINT = "如确有特殊原因，可按制度 2.6 提交特殊申请（须经教务管理员确认）。"


def _has_ineligible(messages: list[dict[str, Any]]) -> bool:
    """本会话是否出现过资格校验不通过的结果。"""
    for m in messages:
        if m.get("role") != "tool":
            continue
        try:
            data = json.loads(m["content"])
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("eligible") is False:
            return True
    return False


def _ensure_special_hint(content: str, messages: list[dict[str, Any]]) -> str:
    """资格不符时补上制度 2.6 特殊申请出口（评测 U08 暴露的遗漏）。"""
    if not content or "特殊申请" in content or not _has_ineligible(messages):
        return content
    return f"{content}\n{_SPECIAL_APPROVAL_HINT}"


def _tool_citations(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从工具结果中提取引用来源（search_selection_rules 返回的条文片段）。

    背景：真实供应商常在"工具检索 → 直答"路径作答，此时不走 RAG 兜底分支，
    若不回填 citations，前端与审计都会缺失引用来源（评测 R01-R07 暴露）。
    """
    cites: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for m in messages:
        if m.get("role") != "tool":
            continue
        try:
            data = json.loads(m["content"])
        except (json.JSONDecodeError, TypeError):
            continue
        for r in data.get("rules") or []:
            key = (r.get("source"), r.get("heading"), r.get("chunk_no"))
            if key in seen:
                continue
            seen.add(key)
            cites.append({"index": len(cites) + 1, "source": r.get("source", ""),
                          "heading": r.get("heading", ""),
                          "chunk_no": r.get("chunk_no"),
                          "preview": (r.get("content") or "")[:60]})
    return cites


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
    result_box.setdefault("citations", [])
    result_box["tools_used"] = []

    # 越权/违规意图先拦截：标准化拒答，不进入工具循环（不写入、不查他人数据）
    refusal = _safety_refusal(question)
    if refusal:
        result_box["answer"] = refusal
        for piece in _split_stream(refusal):
            yield _sse("message", {"delta": piece})
        await log_decision(conv_id, 1, "__safety_refusal__",
                           {"question": question[:60]}, 0, refusal[:200])
        return

    # Agent 路径消息：系统提示词（含工具约束） + 历史 + 脱敏问题。
    # 注意不预置 RAG 上下文 —— 制度依据由模型按需调 search_selection_rules 获取。
    messages: list[dict[str, Any]] = [
        # 系统提示词末尾注入可查询课程清单（运行时生成，防止模型编造课程）
        {"role": "system", "content": with_course_catalog(system_prompt)},
        *history,
        {"role": "user", "content": f"【学生问题】\n{sanitize_for_llm(question)}"},
    ]
    tools_schema = get_tool_schemas()
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
            used_tools = any(m.get("role") == "tool" for m in messages)

            # 代码层硬约束（评测 M04.2 暴露）：学生回复确认语、且会话已有选课意向
            # （查过课程要求/资格）时，模型不得零工具直接口头答复——必须先校验资格，
            # 校验通过则建申请。命中即把决策打回，附约束说明让模型重新决策。
            if (not used_tools and _CONFIRM_REPLY_PATTERN.match(question)
                    and (_presented_selection(_prior_turns(messages))
                         or await _has_prior_intent(conv_id))):
                messages.append({
                    "role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "【系统约束】学生已回复确认语。你必须先调用 "
                               "validate_eligibility 校验资格（尚未校验时）；校验通过后"
                               "紧接着调用 create_selection_application 生成申请单，"
                               "不得只口头答复。校验不通过则如实告知原因。"})
                await log_decision(conv_id, round_no, "__confirm_nudge__",
                                   {"question": question[:60]}, 0,
                                   "确认语零工具直答被打回，要求走校验/建单流程")
                continue

            # 代码层硬约束（评测 R05 暴露的真实供应商问题）：一次工具都没调、
            # 且答案不是安全拒答/引导话术 → 判定"未检索就作答"，丢弃模型自由
            # 发挥的内容，强制改走 RAG 直答（附检索到的制度条文与引用来源）。
            if content and not used_tools and _looks_ungrounded(content):
                content = None

            if content:
                # 资格不符时补制度 2.6 特殊申请出口（评测 U08 暴露的遗漏）
                content = _ensure_special_hint(content, messages)
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

            # 工具检索→直答路径：引用来源从工具结果回填
            #（RAG 兜底分支已在上面赋值；此处置空则是真实供应商工具直答的场景）
            if not result_box["citations"]:
                result_box["citations"] = _tool_citations(messages)

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
            elif (name == "create_selection_application"
                  and not await _check_confirm_gate(conv_id, messages, question)):
                # 确认门状态化硬约束（评测 M01/M05）：未呈现选课信息、或学生本轮
                # 未给出确认语，不得创建申请单，避免替学生做主
                result = {"error": "尚未完成「复述课程信息 → 学生本人确认」的前置步骤，"
                                   "不能创建选课申请。请先说明课程要求与课表信息，然后"
                                   "询问学生是否确认选这门课，待学生回复确认后再创建。"}
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
