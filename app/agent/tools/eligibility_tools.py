# -*- coding: utf-8 -*-
"""资格校验与申请创建工具（阶段4，提示词7）——Agent 的核心安全层。

- validate_eligibility（工具4，只读）：规则引擎逐项校验
    先修课（制度 2.2）→ 重复选课 → 时间冲突（2.3）→ 学分上限（2.4）→ 容量（1.3），
  通过后把课程代码登记进 ctx.validated_courses（确认门依据）。
- create_selection_application（工具5，受控写入）：
    双层防护 —— ① 代码层硬约束：本会话未 validate 通过一律拒绝（模型提示词
    被注入也无法绕过）；② 申请单只落 draft 状态，须学生确认 + 教务审核
    （制度 2.6/2.7：系统只读不代选、特殊申请须教务确认，f05/f33）。
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from ...db import AsyncSessionLocal
from ...models import SelectionApplication
from . import mock_data as md
from .course_tools import resolve_course


# ══════════ 工具4：资格校验（规则引擎，只读）══════════

async def validate_eligibility(ctx, arguments: dict[str, Any]) -> dict[str, Any]:
    """对学生选修指定课程做逐项资格校验；通过则登记进确认门状态。"""
    keyword = str(arguments.get("course_name_or_code", "")).strip()
    student_no = ctx.student_no

    resolved = resolve_course(keyword)
    if resolved is None:
        return {"eligible": False, "checks": [],
                "conclusion": f"未找到课程「{keyword}」，请核对课程名称或代码。"}
    if "ambiguous" in resolved:
        return {"eligible": False, "checks": [],
                "conclusion": "匹配到多门课程，请先确认具体课程后再校验。"}

    # 所有早退分支都携带课程字段：调用方（模型/决策器）需据此判断
    # "该校验结果归属哪门课程"，缺失会导致重复调用（阶段4 实测踩坑）
    course = resolved["course"]

    # 0) 学籍检查：教师/管理员等无学籍账号明确拒绝（不猜测、不代查）
    if not student_no or student_no not in md.MOCK_STUDENTS:
        return {"eligible": False, "checks": [],
                "course_code": course["code"], "course_name": course["name"],
                "conclusion": "当前账号无学生学籍信息，无法进行选课资格校验。"}

    student = md.MOCK_STUDENTS[student_no]
    checks: list[dict[str, Any]] = []
    grades = md.MOCK_GRADES.get(student_no, {})
    enrolled = md.MOCK_ENROLLED.get(student_no, [])

    # 1) 重复选课检查（同一学期不得重复选修）
    dup = next((e for e in enrolled if e["course_code"] == course["code"]), None)
    checks.append({
        "item": "重复选课", "rule": "选课常识校验",
        "passed": dup is None,
        "detail": (f"本学期已选《{dup['course_name']}》，不得重复选修" if dup
                   else "未重复选修"),
    })

    # 2) 先修课检查（制度 2.2：先修课程须 60 分及以上，未达标转人工审核）
    for pre_code in course["prerequisites"]:
        pre_name = md.MOCK_COURSES.get(pre_code, {}).get("name", pre_code)
        score = grades.get(pre_code)
        if score is None:
            passed, detail = False, f"先修课《{pre_name}》（{pre_code}）尚未修读"
        elif score < md.PASS_SCORE:
            passed, detail = False, (f"先修课《{pre_name}》成绩 {score} 分，"
                                     f"低于合格线 {md.PASS_SCORE} 分")
        else:
            passed, detail = True, f"先修课《{pre_name}》成绩 {score} 分（≥{md.PASS_SCORE}）"
        checks.append({"item": "先修课", "rule": "制度 2.2",
                       "passed": passed, "detail": detail})

    # 3) 时间冲突检查（制度 2.3：同一时段不得选修两门课程）
    target_slots = md.MOCK_SCHEDULE.get(course["code"], [])
    conflicts = [e for e in enrolled for s in target_slots
                 if e["weekday"] == s["weekday"] and e["period"] == s["period"]]
    checks.append({
        "item": "时间冲突", "rule": "制度 2.3",
        "passed": not conflicts,
        "detail": ("；".join(f"与已选《{c['course_name']}》{c['weekday']}{c['period']}冲突"
                            for c in conflicts) if conflicts else "与已选课程时段无冲突"),
    })

    # 4) 学分上限检查（制度 2.4：每学期不超过 28 学分；下限 16 在学期末校验）
    enrolled_credits = sum(e["credits"] for e in enrolled)
    total = enrolled_credits + course["credits"]
    checks.append({
        "item": "学分上限", "rule": "制度 2.4",
        "passed": total <= md.CREDIT_LIMIT_MAX,
        "detail": (f"已选 {enrolled_credits} + 本课 {course['credits']} = {total} 学分，"
                   f"超过上限 {md.CREDIT_LIMIT_MAX}" if total > md.CREDIT_LIMIT_MAX else
                   f"已选 {enrolled_credits} + 本课 {course['credits']} = {total} 学分"
                   f"（上限 {md.CREDIT_LIMIT_MAX}，下限 {md.CREDIT_LIMIT_MIN} 于补退选后校验）"),
    })

    # 5) 容量检查（制度 1.3：选课人数不得超过教室容量）
    cap = course["capacity"]
    checks.append({
        "item": "课程容量", "rule": "制度 1.3",
        "passed": cap["enrolled"] < cap["max"],
        "detail": f"已选 {cap['enrolled']} / 容量 {cap['max']}",
    })

    eligible = all(c["passed"] for c in checks)
    result = {
        "student_no": student_no, "student_name": student["name"],
        "semester": md.SEMESTER,
        "course_code": course["code"], "course_name": course["name"],
        "course_type": course["type"], "credits": course["credits"],
        "eligible": eligible, "checks": checks,
        "conclusion": ("符合选课资格" if eligible else
                       "不符合选课资格；如确有特殊需要，可按制度 2.6 提交特殊申请，"
                       "由教务管理员人工确认"),
        "rule_version": md.RULE_VERSION,       # 依据的制度版本（审计"资料版本"）
    }

    # 确认门登记：仅"完全通过"的课程才允许后续 create（硬约束依据）
    if eligible:
        ctx.validated_courses.add(course["code"])
        ctx.validated_results[course["code"]] = result
    return result


# ══════════ 工具5：创建选课申请（受控写入 + 确认门）══════════

def _gen_business_no() -> str:
    """生成业务编号：XK + 日期时间(14位) + 2 位随机（审计"业务编号"要素，f45）。"""
    return "XK" + datetime.now().strftime("%Y%m%d%H%M%S") + f"{random.randint(10, 99)}"


async def create_selection_application(ctx, arguments: dict[str, Any]) -> dict[str, Any]:
    """为通过资格校验的课程创建 draft 选课申请单（不直接选课，f05）。

    硬约束（代码层，无法被提示词绕过）：
        课程代码必须在 ctx.validated_courses 中（本会话 validate_eligibility 通过）。
    """
    keyword = str(arguments.get("course_name_or_code", "")).strip()

    resolved = resolve_course(keyword)
    if resolved is None or "ambiguous" in resolved:
        return {"created": False,
                "message": f"无法确定课程「{keyword}」，请先确认课程名称或代码。"}
    course = resolved["course"]

    # ── 确认门硬约束：未校验 / 校验未通过 → 一律拒绝 ──
    if course["code"] not in ctx.validated_courses:
        return {"created": False,
                "message": "操作被安全策略拦截：创建选课申请前，必须先调用 "
                           "validate_eligibility 且校验通过（制度 2.2/2.3/2.4）。"
                           "请先为学生完成资格校验。"}

    if not ctx.student_no or ctx.student_no not in md.MOCK_STUDENTS:
        return {"created": False, "message": "当前账号无学生学籍信息，无法创建选课申请。"}

    student = md.MOCK_STUDENTS[ctx.student_no]
    eligibility = ctx.validated_results[course["code"]]   # 与校验结论保持一致

    application = {
        "business_no": _gen_business_no(),
        "status": "draft",                            # 待学生确认（f33）
        "student": {"no": ctx.student_no, "name": student["name"]},
        "course": {"code": course["code"], "name": course["name"],
                   "credits": course["credits"], "type": course["type"]},
        "semester": md.SEMESTER,
        "eligibility": eligibility,
        # 依据条文与版本（审计五要素之"资料版本"）
        "rule_refs": [md.RULE_VERSION,
                      "制度 2.2 先修课 / 2.3 时间冲突 / 2.4 学分上限 / 2.7 选课结果确认",
                      f"课表版本 {md.SCHEDULE_VERSION}"],
        "confirm_hint": "申请单已生成（草稿状态）。系统不代替学生选课：请学生本人"
                        "在确认卡片上点击【确认提交】，申请将提交教务管理员审核"
                        "（制度 2.7）。",
    }

    # 落库（draft 状态；学生确认走 POST /api/chat/confirm，教务审核走管理端）
    async with AsyncSessionLocal() as db:
        db.add(SelectionApplication(
            business_no=application["business_no"],
            conversation_id=ctx.conversation_id,
            user_id=ctx.user_id,
            student_no=ctx.student_no,
            student_name=student["name"],
            semester=md.SEMESTER,
            course_code=course["code"],
            course_name=course["name"],
            credits=course["credits"],
            eligibility_result=eligibility,
            rule_refs=application["rule_refs"],
            status="draft",
        ))
        await db.commit()

    ctx.pending_application = application       # 供 Agent 循环发确认事件
    return {"created": True, **application}
