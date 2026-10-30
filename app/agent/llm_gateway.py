# -*- coding: utf-8 -*-
"""LLM 网关（阶段4 扩展，提示词7）：供应商可配置 + 出校脱敏 + 决策/流式双通道。

- 供应商可配置：mock（离线冒烟+脚本化工具决策）/ openai_compatible（真实调用）；
- complete_llm()：Agent 决策轮（非流式，带 tools 参数，返回 tool_calls 或纯文本）；
- stream_llm()：普通制度问答的流式直答（阶段1-3 行为，保持兼容）；
- 出校脱敏（Q6）：学号/手机号/证件号在发往外部 LLM 前替换为占位符；
- 统一抛 ApiError（50301 调用失败 / 50302 配置错误），绝不静默失败。

说明：决策轮必须拿到完整结果才能解析 tool_calls（流式中途无法判断模型是否
要调工具），故 complete_llm 采用非流式；最终回答由 agent_loop 切块回放模拟
流式（真实供应商下如需逐 token 推送，可在确认"无工具调用"后改为二次流式
请求，代价是两次调用结果可能不一致，故本阶段选择确定性优先）。

【阶段5 评测驱动增强（提示词8）】mock 决策器新增三项能力（离线评测用例所需）：
1. 代理意图拒绝：检测"替室友/代同学选课"等代他人办理意图 → 直接拒绝；
2. 代词回指：'那这门课我能选吗'从上文助手回答中解析《课程名》；
3. 目标切换重查：选课流程中学生改选另一门课时，重新查询新课程要求。
"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

import jieba

from ..config import settings
from ..schemas import ApiError, ErrorCode


def sanitize_for_llm(text: str) -> str:
    """出校脱敏（Q6 默认答案，简版）：学号/手机号/证件号 → 占位符。

    后续扩展：姓名词典 + 占位符本地回填。
    """
    text = re.sub(r"\b\d{10,12}\b", "[学号已脱敏]", text)
    text = re.sub(r"\b1[3-9]\d{9}\b", "[手机号已脱敏]", text)
    text = re.sub(r"\b\d{17}[\dXx]\b", "[证件号已脱敏]", text)
    return text


# ══════════ 决策轮：非流式（带 Function Calling）══════════

async def complete_llm(messages: list[dict[str, Any]],
                       tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Agent 决策调用：返回 {content, tool_calls, finish_reason}。

    - tool_calls：[{"id", "name", "arguments"(dict)}]，为 None 表示模型决定直答；
    - content：模型给出的文本（直答时即最终回答；调工具时通常为 None）。
    """
    if settings.llm_provider == "mock":
        return _mock_decide(messages)

    if settings.llm_provider != "openai_compatible" or not settings.llm_api_key:
        raise ApiError(ErrorCode.LLM_CONFIG_ERROR,
                       "请检查 .env 中的 LLM_PROVIDER / LLM_API_KEY 等配置")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=settings.llm_base_url or None,
                             api_key=settings.llm_api_key,
                             timeout=settings.llm_timeout, max_retries=1)
        kwargs: dict[str, Any] = dict(model=settings.llm_model, messages=messages,
                                      temperature=0.1)   # 低温度：决策稳定
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = await client.chat.completions.create(**kwargs)

        choice = resp.choices[0]
        msg = choice.message
        calls = None
        if getattr(msg, "tool_calls", None):
            calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {"_raw": tc.function.arguments}   # 参数非法 → 原样带回
                calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
        return {"content": msg.content, "tool_calls": calls,
                "finish_reason": choice.finish_reason}
    except ApiError:
        raise
    except Exception as exc:   # noqa: BLE001 —— 网络/供应商异常统一转中文错误
        raise ApiError(ErrorCode.LLM_ERROR,
                       f"供应商={settings.llm_provider} 模型={settings.llm_model}，{exc}")


# ══════════ 流式直答（阶段1-3 原路径，保持兼容）══════════

async def stream_llm(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """调用 LLM 流式生成回答，异步 yield 文本增量。"""
    if settings.llm_provider == "mock":
        # 离线冒烟：不联网，验证"检索→装配→流式"整条链路
        async for piece in _mock_llm(messages):
            yield piece
        return

    if settings.llm_provider != "openai_compatible" or not settings.llm_api_key:
        raise ApiError(ErrorCode.LLM_CONFIG_ERROR,
                       "请检查 .env 中的 LLM_PROVIDER / LLM_API_KEY 等配置")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=settings.llm_base_url or None,
                             api_key=settings.llm_api_key,
                             timeout=settings.llm_timeout, max_retries=1)
        stream = await client.chat.completions.create(
            model=settings.llm_model, messages=messages,
            stream=True, temperature=0.1)   # 低温度：制度问答要求稳定、不发散
        async for delta in stream:
            piece = delta.choices[0].delta.content if delta.choices else None
            if piece:
                yield piece
    except ApiError:
        raise
    except Exception as exc:   # noqa: BLE001 —— 网络/供应商异常类型多，统一转中文错误
        raise ApiError(ErrorCode.LLM_ERROR,
                       f"供应商={settings.llm_provider} 模型={settings.llm_model}，{exc}")


async def _mock_llm(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """
    mock 供应商（仅离线冒烟用）：用"词面重叠抽取"模拟回答。
    - 与问题零词面重叠 → 回答"制度中未找到"（模拟陷阱题的正确行为）；
    - 有重叠 → 从最佳片段按重叠数抽取句子并附引用。
    生产环境必须切换真实供应商；"未找到"的判断在生产中由 LLM 依据系统提示词完成。
    """
    user_msg = messages[-1]["content"]

    m = re.search(r"【学生问题】\s*(.+)$", user_msg, re.S)
    question = m.group(1).strip() if m else ""
    q_tokens = {t for t in jieba.lcut(question) if len(t) > 1}

    blocks = re.findall(r"\[(\d+)\] 来源：([^\n]+)\n(.*?)(?=\n\n\[|\n\n【|$)",
                        user_msg, re.S)

    scored = []
    for no, src, body in blocks:
        b_tokens = {t for t in jieba.lcut(body) if len(t) > 1}
        overlap = len(q_tokens & b_tokens)
        if overlap > 0:
            # 平手时优先检索排名靠前的片段（RRF 融合序更可信），
            # 避免按编号字符串比较任意择块（提示词8 · R07 实测踩坑）
            scored.append((overlap, -int(no), no, src, body))

    if not scored:   # 陷阱题：检索上下文与问题零重叠
        yield "（mock 供应商·离线演示）制度中未找到与该问题相关的条文。建议换一种问法，或咨询教务管理员。"
        return

    scored.sort(reverse=True)
    _, _, no, src, body = scored[0]
    # 抽取句子：按与问题的词面重叠数降序取前 3 句（确定性输出，便于冒烟比对）
    scored_sent = []
    for sent in re.split(r"[。；;]", body):
        s_tokens = {t for t in jieba.lcut(sent) if len(t) > 1}
        cleaned = sent.strip(" ：:，,\n\t ")
        overlap = len(s_tokens & q_tokens)
        if overlap > 0 and len(cleaned) > 4:
            scored_sent.append((overlap, cleaned))
    scored_sent.sort(reverse=True)
    yield f"（mock 供应商·离线演示）根据制度条文[{no}]：\n"
    for _, s in scored_sent[:3]:
        yield f"· {s}。\n"
    yield f"\n引用来源：[{no}] {src}\n"


# ══════════ mock 脚本化工具决策（离线验证典型轨迹）══════════
# 以下规则与 eval/eval_cases.json 的用例一一对应（提示词8 评测基线）：
#   制度问答      → tool_calls=None（agent_loop 回退 RAG 直答路径）
#   课表查询      → query_course_schedule
#   课程要求咨询  → check_course_requirements（阶段5 新增意图）
#   资格询问      → validate_eligibility
#   选课意向      → search_selection_rules → check_course_requirements → 确认话术
#                   （学生回复"确认"）→ validate_eligibility → create_selection_application
#   代他人办理    → 直接拒绝（阶段5 新增：代理意图检测）

# 意图关键词表（按优先级排列；mock 专用，真实供应商由模型自主决策）
# 【上线演练发现5修复】补充"上课"等常见问法变体：此前"什么时候上课"类问法
# 未命中课表意图而走 RAG 直答；现命中后若课程不存在，工具会明确返回
# "未找到课程「X」"，不再误引不相关条文（有目标课程才触发工具调用，安全）
_KW_SCHEDULE = ("周几", "星期几", "几点", "课表", "上课时间", "哪个教室",
                "在哪里上", "在哪个教室", "第几节", "几节课", "什么时间上课",
                "上课", "什么时候上", "啥时候")
_KW_REQUIREMENTS = ("先修", "学分是", "多少学分", "学时", "容量", "课程要求",
                    "必修还是选修", "选修还是必修", "什么要求")
_KW_ELIGIBILITY = ("能选", "可以选", "能报", "可以报", "有资格", "资格",
                   "学分不够", "学分不足", "符合条件", "选不了", "能不能选")
_KW_CONFIRM = ("确认", "确定", "是的", "可以", "好的", "好吧", "嗯", "同意",
               "继续", "选它", "就选它", "帮我选吧")
_SELECT_PATTERNS = (re.compile(r"(帮我|我要|我想|给我|请).{0,6}选"),
                    re.compile(r"选修这门"), re.compile(r"报选"))

# 代理意图检测：代他人办理（替室友/代同学选课等）→ 拒绝（制度 2.7：本人操作）
_PROXY_PATTERN = re.compile(
    r"(替|代)(他|她|它|同学|室友|朋友|别人|家长|家人|弟弟|妹妹|学长|学姐)")
_PROXY_REFUSAL = ("抱歉，选课申请须由学生本人发起并确认，我不能代替他人办理"
                  "（制度 2.7）。请让你的同学使用本人账号登录后自行操作。")


def _extract_course(text: str) -> str | None:
    """从文本提取课程关键词：《课程名》优先，其次课程名词表/代码包含匹配。"""
    if not text:
        return None
    m = re.search(r"《([^《》]{2,20})》", text)
    if m:
        return m.group(1)
    # 延迟导入避免模块级循环依赖（mock_data 无外部依赖，实为安全导入）
    from .tools import mock_data as md
    for c in md.MOCK_COURSES.values():
        if c["name"] in text:
            return c["name"]
    m = re.search(r"\b(CS\d{3}|MT\d{3})\b", text.upper())
    if m and m.group(1) in md.MOCK_COURSES:
        return m.group(1)
    return None


def _extract_target(question: str, messages: list[dict[str, Any]]) -> str | None:
    """提取目标课程：先从当前问题提取，失败则回指上文（代词'这门课'场景）。

    【阶段5 评测驱动增强】：多轮对话中学生常用"那这门课我能选吗"这类指代，
    需从最近的助手回答中解析《课程名》（真实供应商由模型自主完成指代消解）。
    """
    target = _extract_course(question)
    if target:
        return target
    for m in reversed(messages):
        if m.get("role") == "assistant" and m.get("content"):
            mm = re.search(r"《([^《》]{2,20})》", m["content"])
            if mm:
                return mm.group(1)
    return None


def _tool_results(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """收集消息流中已回填的工具结果（按时间正序）。"""
    out = []
    for m in messages:
        if m.get("role") == "tool":
            try:
                out.append(json.loads(m["content"]))
            except (json.JSONDecodeError, TypeError):
                continue
    return out


def _has_result(results: list[dict], *keys: str) -> dict | None:
    """按结果字典的判别键查找最近一次工具结果（如 schedule=课表查询）。"""
    for r in reversed(results):
        if all(k in r for k in keys):
            return r
    return None


def _norm_course_name(keyword: str) -> str | None:
    """把课程关键词解析为规范课程名（用于结果归属比对）。"""
    from .tools import mock_data as md
    from .tools.course_tools import resolve_course
    resolved = resolve_course(keyword)
    if resolved and "course" in resolved:
        return resolved["course"]["name"]
    return None


def _last_call_keyword(messages: list[dict[str, Any]], tool: str) -> str | None:
    """取最近一次指定工具调用的 course_name_or_code 参数。

    【上线演练发现5修复】判重依据从"结果结构"改为"调用参数"：
    课程不存在时工具返回 {found, message}（无 schedule/course_type 等判别键），
    按结果判重会永远视为"未查过"而反复重查耗尽轮次。

    消息格式兼容：agent_loop 回填的 assistant 消息为 OpenAI 原生格式
    （tool_calls[].function.name + arguments 为 JSON 字符串）。
    """
    for m in reversed(messages):
        if m.get("role") != "assistant" or not m.get("tool_calls"):
            continue
        for tc in m["tool_calls"]:
            fn = tc.get("function") or {}
            name = fn.get("name") or tc.get("name")
            if name != tool:
                continue
            raw_args = fn.get("arguments", tc.get("arguments"))
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    raw_args = {}
            return str((raw_args or {}).get("course_name_or_code", ""))
    return None


def _already_queried(messages: list[dict[str, Any]], tool: str, target: str) -> bool:
    """目标课程是否已用该工具查过：原文相等（覆盖不存在的课程）或归一化相等
    （同一门课的不同写法，如代码 CS101 与课程名）。"""
    last = _last_call_keyword(messages, tool)
    if last is None:
        return False
    if last == target:
        return True
    norm = _norm_course_name(last)
    return norm is not None and norm == _norm_course_name(target)


def _last_tool_result(messages: list[dict[str, Any]],
                      tool: str) -> dict[str, Any] | None:
    """最近一次指定工具调用的执行结果（按 tool_call_id 配对消息，不依赖结果结构）。

    【发现5修复】与 _has_result 的区别：工具"未找到课程"时返回 {found, message}，
    不含 schedule/course_type 等判别键，按判别键查找会漏掉该结果——
    本函数按调用配对，任何形态的结果都能取到。
    """
    for m in reversed(messages):
        if m.get("role") != "assistant" or not m.get("tool_calls"):
            continue
        for tc in m["tool_calls"]:
            fn = tc.get("function") or {}
            if (fn.get("name") or tc.get("name")) != tool:
                continue
            call_id = tc.get("id")
            for t in messages:
                if t.get("role") == "tool" and t.get("tool_call_id") == call_id:
                    try:
                        return json.loads(t["content"])
                    except (json.JSONDecodeError, TypeError):
                        return None
    return None


def _mock_final_answer(messages: list[dict[str, Any]],
                       question: str, intent: str = "") -> str | None:
    """根据已回填的工具结果拼装最终回答（确定性输出，便于离线比对）。

    intent 参数区分话术形态（阶段5 新增）：
    - "requirements"：课程要求咨询 → 输出要求明细，不请求确认；
    - 其他：维持原行为（选课确认话术等）。
    返回 None 表示"无工具结果可拼"→ 由 agent_loop 回退 RAG 直答路径。
    """
    results = _tool_results(messages)

    # 1) 资格校验结论（资格询问 / 选课确认后的校验分支）
    v = _has_result(results, "eligible")
    if v is not None and v.get("course_code"):
        if v.get("eligible"):
            lines = [f"资格校验通过 ✅：你可以选修《{v['course_name']}》（{v['course_code']}，"
                     f"{v.get('course_type', '')}，{v.get('credits', 0)} 学分）。"]
            for c in v.get("checks", []):
                mark = "✓" if c.get("passed") else "✗"
                lines.append(f"· [{mark}] {c['item']}：{c['detail']}（{c['rule']}）")
            lines.append(f"依据：{v.get('rule_version', '')}。")
            return "\n".join(lines)
        lines = [f"经校验，你目前不符合《{v['course_name']}》（{v['course_code']}）的选修资格 ❌："]
        for c in v.get("checks", []):
            if not c.get("passed"):
                lines.append(f"· {c['item']}：{c['detail']}（{c['rule']}）")
        lines.append(v.get("conclusion", "") + "。")
        return "\n".join(lines)
    # 【发现5修复】课程未找到/歧义（无 course_code）：直接输出工具结论，
    # 避免落入兜底 RAG 误引不相关条文
    if v is not None and v.get("eligible") is False and not v.get("course_code"):
        return v.get("conclusion") or "未找到该课程，请核对课程名称或代码。"

    # 2) 课表回答（【发现5修复】按调用配对取结果：未找到课程时同样能取到）
    s = _last_tool_result(messages, "query_course_schedule")
    if s is not None:
        if s.get("found") and s.get("schedule"):
            parts = [f"《{s['course_name']}》（{s['course_code']}）{s['semester']} 学期排课："]
            for slot in s["schedule"]:
                parts.append(f"· {slot['weekday']} {slot['period']}，{slot['room']}，"
                             f"{slot['teacher']}（{slot['weeks']}）")
            parts.append(f"课表版本：{s['version']}，数据更新于 {s['data_updated_at']}。")
            parts.append(s.get("stale_hint", ""))
            return "\n".join(parts)
        return s.get("message", "未查询到该课程的排课信息。")

    # 3) 课程信息（按意图输出"要求明细"或"选课确认话术"；含未找到课程）
    c = _last_tool_result(messages, "check_course_requirements")
    if c is not None and not c.get("found", True):
        return c.get("message", "未找到该课程，请核对课程名称或代码。")
    if c is not None and c.get("course_type"):
        pres = c.get("prerequisites") or []
        pres_text = ("、".join(f"《{p['name']}》（{p['code']}）" for p in pres)
                     if pres else "无")
        if intent == "requirements":
            # 课程要求咨询：客观陈述要求，不发起选课流程
            return (f"《{c['course_name']}》（{c['course_code']}）课程要求：\n"
                    f"· 类型：{c['course_type']}；学分：{c['credits']}；学时：{c['hours']}\n"
                    f"· 先修课：{pres_text}（制度 2.2：先修课须 60 分及以上）\n"
                    f"· 选课容量：已选 {c['capacity']['enrolled']} / {c['capacity']['max']}\n"
                    f"依据：{c.get('credit_rule', '制度 3.1')}。")
        # 选课意向：复述课程信息 + 请求学生确认（确认门第一段）
        return (f"已为你查询到课程信息：\n"
                f"· 《{c['course_name']}》（{c['course_code']}），{c['college']}开设，"
                f"{c['course_type']}课，{c['credits']} 学分 / {c['hours']} 学时\n"
                f"· 先修课要求：{pres_text}（制度 2.2：先修课须 60 分及以上）\n"
                f"· 选课容量：已选 {c['capacity']['enrolled']} / {c['capacity']['max']}\n\n"
                f"确认要选这门课吗？回复「确认」，我将为你校验选课资格并生成选课申请单"
                f"（申请须经你本人确认与教务管理员审核，系统不代替选课，制度 2.7）。")

    return None


def _mock_decide(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """mock 决策器：按意图规则产出确定性的 tool_calls / 最终回答。"""
    # 当前学生问题 = 最后一条 user 消息
    user_msg = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    text = user_msg.get("content", "")
    m = re.search(r"【学生问题】\s*(.+)$", text, re.S)
    question = (m.group(1) if m else text).strip()
    results = _tool_results(messages)

    def _call(name: str, **args) -> dict[str, Any]:
        return {"content": None,
                "tool_calls": [{"id": f"call_{name}", "name": name, "arguments": args}],
                "finish_reason": "tool_calls"}

    def _final(content: str) -> dict[str, Any]:
        return {"content": content, "tool_calls": None, "finish_reason": "stop"}

    # ── 意图0：代他人办理（替室友/代同学选课）→ 直接拒绝（安全边界）──
    if _PROXY_PATTERN.search(question):
        return _final(_PROXY_REFUSAL)

    # ── 意图1：学生对上一轮"选课确认话术"的确认回复 ──
    last_assistant = next((m.get("content") or "" for m in reversed(messages)
                           if m.get("role") == "assistant" and m.get("content")), "")
    confirm_context = ("确认要选" in last_assistant or "确认选" in last_assistant)
    if (confirm_context and len(question) <= 16
            and any(w in question for w in _KW_CONFIRM)):
        target = _extract_target(question, messages)
        if target:
            # 已校验且通过 → 建申请；未校验 → 先校验（调用顺序约束）
            v = _has_result(results, "eligible")
            if not _already_queried(messages, "validate_eligibility", target):
                return _call("validate_eligibility", course_name_or_code=target)
            if v is not None and v.get("eligible"):
                return _call("create_selection_application",
                             course_name_or_code=target)
            return _final(_mock_final_answer(messages, question))

    # ── 意图2：课表查询 ──
    if any(w in question for w in _KW_SCHEDULE):
        target = _extract_target(question, messages)
        if target:
            # 【发现5修复】按调用参数判重（结果判重对不存在的课程失效）
            if not _already_queried(messages, "query_course_schedule", target):
                return _call("query_course_schedule", course_name_or_code=target)
            return _final(_mock_final_answer(messages, question))

    # ── 意图3：课程要求咨询（先修/学分/学时/容量/类型）──
    if any(w in question for w in _KW_REQUIREMENTS):
        target = _extract_target(question, messages)
        if target:
            if not _already_queried(messages, "check_course_requirements", target):
                return _call("check_course_requirements", course_name_or_code=target)
            return _final(_mock_final_answer(messages, question,
                                             intent="requirements"))

    # ── 意图4：资格询问 ──
    if any(w in question for w in _KW_ELIGIBILITY):
        target = _extract_target(question, messages)
        if target:
            if not _already_queried(messages, "validate_eligibility", target):
                return _call("validate_eligibility", course_name_or_code=target)
            return _final(_mock_final_answer(messages, question))

    # ── 意图5：选课意向（规则→课程要求→确认话术；目标切换时重查）──
    if any(p.search(question) for p in _SELECT_PATTERNS):
        target = _extract_target(question, messages)
        if target:
            # 顺序约束：先查制度规则（同会话只需一次）
            if _has_result(results, "rules") is None:
                return _call("search_selection_rules",
                             query="下学期选课规则 先修课要求 时间冲突 学分上限")
            # 课程要求：未查过、或学生已改选另一门课 → 重新查询
            if not _already_queried(messages, "check_course_requirements", target):
                return _call("check_course_requirements", course_name_or_code=target)
            return _final(_mock_final_answer(messages, question, intent="select"))

    # ── 兜底：无工具意图 → 直答（agent_loop 用 RAG 上下文走 stream_llm）──
    return {"content": None, "tool_calls": None, "finish_reason": "stop"}
