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
# 说明：_OLD_DEFAULT_SYSTEM_PROMPT 保留上一版原文，既用于合成新默认，
# 也放入 LEGACY_DEFAULT_PROMPTS 以便未自定义过的库模板平滑升级（见 prompt_service）。
_OLD_DEFAULT_SYSTEM_PROMPT = (
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

_V2_DEFAULT_SYSTEM_PROMPT = _OLD_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【模糊提问】学生问'我该选什么课/选哪门课'这类未给出课程名的问题时，说明制度只"
    "规定选课规则、不提供推荐课程，请其提供课程名或课程代码，并列出可查询的课程示例；"
    "不得臆测推荐课程。\n"
    "【数据时效】",
)

_V3_DEFAULT_SYSTEM_PROMPT = _V2_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【规则类问题】学生询问制度规则（如学分上限、时间冲突如何处理、选课时间、毕业"
    "学分）时，必须先调 search_selection_rules 并直接依据条文作答，不得反问课程名或"
    "把规则问题推给教务系统。\n"
    "【数据时效】",
)

_V4_DEFAULT_SYSTEM_PROMPT = _V3_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【越权与流程】学生要求「跳过审核 / 免审批 / 直接把课程加入课表」时，明确拒绝并"
    "说明选课必须走「申请 → 本人确认 → 教务管理员审核」流程（制度 2.7），不得创建"
    "选课申请单；学生要求查询他人（同学/室友/他人）的课表、成绩等个人信息时，拒绝并"
    "说明只提供本人数据，且不要复述对方姓名。\n"
    "【数据时效】",
)

# 上一版默认提示词（含【确认流程】）：保留用于识别旧模板并平滑升级
_PREV_DEFAULT_SYSTEM_PROMPT = _V4_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【确认流程】学生回复「确认 / 确定 / 好的 / 可以」表示同意选课时，必须先调用"
    " validate_eligibility（尚未校验时），校验通过后立即调用 "
    "create_selection_application 生成申请单（系统会发确认卡片），不得只口头回复"
    "校验结果。\n"
    "【数据时效】",
)

# 当前版默认提示词（【流程强制】v2）：先存为变量，供下一版合成与 LEGACY 识别
_V5_DEFAULT_SYSTEM_PROMPT = _PREV_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【流程强制】真实供应商常省略中间步骤，以下为硬性顺序要求："
    "1) 学生提出「帮我选某门课」时，第一轮必须先 search_selection_rules、再 "
    "check_course_requirements，两步缺一不可，然后输出确认话术；第一轮不得调用 "
    "validate_eligibility 或 create_selection_application。"
    "2) 学生以任何形式询问自己是否具备选课资格——包括「能不能选 / 还能选吗 / "
    "是不是重复选过 / 学分不够能选吗 / 先修没修能选吗」——都必须调用 "
    "validate_eligibility 并依据其返回结果作答，不得凭记忆或制度推断。"
    "3) 学生只问排课时间、教室、学分、先修课、课程类型时，只调用对应查询工具，"
    "不进入选课流程。"
    "4) 同一会话内已查过制度规则可复用，但换了目标课程必须重新查该课程要求。\n"
    "【数据时效】",
)

DEFAULT_SYSTEM_PROMPT = _V5_DEFAULT_SYSTEM_PROMPT.replace(
    "【数据时效】",
    "【确认与收尾】学生回复「确认 / 确定 / 好的 / 可以 / 是」时：若本会话尚未对该课程"
    "调用 validate_eligibility，必须先校验；校验通过后【必须紧接着】调用 "
    "create_selection_application 生成申请单，不得在校验通过后停步、只口头汇报校验结果。"
    "若学生表达选课意向（如「那帮我选这门课吧」）但尚未给出过确认答复，则不得创建申请，"
    "须先 check_course_requirements 复述课程信息并输出确认话术，等学生回复确认后再创建。"
    "注意：资格校验通过只代表学生【具备资格】，不代表学生【同意选课】，二者不得混同。\n"
    "【数据时效】",
)

# ── 历史版本默认提示词（阶段2/3 及阶段4 早期）：用于识别"未被自定义编辑"的旧模板并平滑升级 ──
LEGACY_DEFAULT_PROMPTS: list[str] = [
    DEFAULT_SYSTEM_PROMPT.replace(
        "注意：资格校验通过只代表学生【具备资格】，不代表学生【同意选课】，二者不得混同。\n",
        "\n"),  # 【确认与收尾】v1（无资格/确认区分句）
    _V5_DEFAULT_SYSTEM_PROMPT,  # 【流程强制】v2（无【确认与收尾】段）
    _V5_DEFAULT_SYSTEM_PROMPT.replace(
        "学生以任何形式询问自己是否具备选课资格——包括「能不能选 / 还能选吗 / "
        "是不是重复选过 / 学分不够能选吗 / 先修没修能选吗」——都必须调用 ",
        "学生问「能不能选 / 还能选吗 / 是不是重复选过」时，必须调用 "),  # 【流程强制】v1
    _PREV_DEFAULT_SYSTEM_PROMPT,
    _V4_DEFAULT_SYSTEM_PROMPT,
    _V3_DEFAULT_SYSTEM_PROMPT,
    _V2_DEFAULT_SYSTEM_PROMPT,
    _OLD_DEFAULT_SYSTEM_PROMPT,
    "你是学校教务制度助手，只根据提供的制度条文回答，不确定时明确说'制度中未找到'，"
    "回答末尾附引用来源，不得编造排课或选课规则。",
]


def course_catalog_text() -> str:
    """生成可查询课程清单（注入系统提示词，约束模型不得编造课程）。

    数据源：mock_data.MOCK_COURSES（接真实教务接口后替换数据源即可，
    装配逻辑与提示词均无需改动）。
    """
    from .tools import mock_data as md
    lines = [f"· {c['name']}（{c['code']}，{c['type']}，{c['credits']} 学分，"
             f"{c['college']}）" for c in md.MOCK_COURSES.values()]
    return "【可查询课程清单（仅以下课程，禁止编造清单外的课程）】\n" + "\n".join(lines)


def with_course_catalog(system_prompt: str) -> str:
    """在系统提示词末尾追加课程清单（运行时生成，课程库变化自动同步）。"""
    return f"{system_prompt}\n\n{course_catalog_text()}"


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
        {"role": "system",
         "content": with_course_catalog(system_prompt or DEFAULT_SYSTEM_PROMPT)},
    ]
    messages.extend(history or [])                       # 多轮上下文（代词指代、追问）
    messages.append({"role": "user", "content": user_msg})
    return messages
