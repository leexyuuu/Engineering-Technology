# -*- coding: utf-8 -*-
"""课程类工具（阶段4，提示词7）：query_course_schedule / check_course_requirements。

设计要点：
- 只读工具：只查询、不写入，任何异常不中断对话（返回结构化错误说明）；
- 课表结果必须带版本号与数据更新时间（制度 3.4），并附 15 分钟同步周期
  的"以教务系统为准"提示（制度 1.6 / 3.5，业务调研 f24）；
- 课程名/代码模糊匹配：学生说"人工智能"也能命中 CS305。
"""
from __future__ import annotations

from typing import Any

from . import mock_data as md


def resolve_course(keyword: str) -> dict[str, Any] | None:
    """按课程代码或名称（包含匹配）解析课程；命中多门时返回歧义提示结构。

    返回：
        - {"course": {...}}      唯一命中
        - {"ambiguous": [...]}   多门命中（跨学院同名等，须人工确认，f40）
        - None                   未命中
    本函数是工具层的公共入口（资格校验/建申请也复用）。
    """
    kw = (keyword or "").strip().replace("《", "").replace("》", "")
    if not kw:
        return None

    # 1) 精确命中课程代码
    if kw.upper() in md.MOCK_COURSES:
        return {"course": md.MOCK_COURSES[kw.upper()]}

    # 2) 名称包含匹配（"人工智能" → "人工智能基础"）
    hits = [c for c in md.MOCK_COURSES.values() if kw in c["name"]]
    if len(hits) == 1:
        return {"course": hits[0]}
    if len(hits) > 1:
        # 多门命中 → 歧义：交由模型向学生澄清，不进入自动推荐（f40）
        return {"ambiguous": [
            {"code": c["code"], "name": c["name"], "college": c["college"]}
            for c in hits]}
    return None


async def query_course_schedule(ctx, arguments: dict[str, Any]) -> dict[str, Any]:
    """工具1：查询指定课程在目标学期的排课（周几/节次/教室/教师/版本）。

    供模型回答"下学期《数据结构》周几上课"这类课表问题（轨迹 a）。
    """
    keyword = str(arguments.get("course_name_or_code", "")).strip()
    resolved = resolve_course(keyword)

    if resolved is None:
        return {"found": False,
                "message": f"未找到课程「{keyword}」，请核对课程名称或代码。"}
    if "ambiguous" in resolved:
        return {"found": False, "ambiguous": True,
                "candidates": resolved["ambiguous"],
                "message": "匹配到多门课程，请学生确认具体是哪一门后再查询。"}

    course = resolved["course"]
    slots = md.MOCK_SCHEDULE.get(course["code"], [])
    if not slots:
        return {"found": False,
                "message": f"《{course['name']}》（{course['code']}）在 "
                           f"{md.SEMESTER} 学期暂无排课记录。"}

    # 课表答案必须带版本号 + 数据更新时间 + 同步周期提示（f24 / 制度 3.4）
    return {
        "found": True,
        "semester": md.SEMESTER,
        "course_code": course["code"],
        "course_name": course["name"],
        "schedule": slots,
        "version": md.SCHEDULE_VERSION,          # 课表版本（学期-版次）
        "data_updated_at": md.SCHEDULE_UPDATED_AT,
        "stale_hint": "课表数据每 15 分钟同步一次，仅供参考，请以教务系统最终数据为准"
                      "（制度 1.6 / 3.5）。",
    }


async def check_course_requirements(ctx, arguments: dict[str, Any]) -> dict[str, Any]:
    """工具2：查询课程要求（类型/学分/学时/先修课/容量）。

    供模型在学生表达选课意向后、生成确认话术前调用（轨迹 b 第 2 步）。
    """
    keyword = str(arguments.get("course_name_or_code", "")).strip()
    resolved = resolve_course(keyword)

    if resolved is None:
        return {"found": False,
                "message": f"未找到课程「{keyword}」，请核对课程名称或代码。"}
    if "ambiguous" in resolved:
        return {"found": False, "ambiguous": True,
                "candidates": resolved["ambiguous"],
                "message": "匹配到多门课程，请学生确认具体是哪一门。"}

    c = resolved["course"]
    # 先修课名称一并返回（学生未必记得代码对应的课程名）
    prereqs = [{"code": p, "name": md.MOCK_COURSES[p]["name"]}
               for p in c["prerequisites"] if p in md.MOCK_COURSES]
    return {
        "found": True,
        "course_code": c["code"],
        "course_name": c["name"],
        "college": c["college"],
        "course_type": c["type"],               # 必修 / 选修
        "credits": c["credits"],
        "hours": c["hours"],
        "credit_rule": "理论课 16 学时计 1 学分；实验实训课 32 学时计 1 学分（制度 3.1）",
        "prerequisites": prereqs,               # 先修课列表（可空）
        "capacity": c["capacity"],              # 已选/容量（制度 1.3 预留 90% 建议）
        "semester": md.SEMESTER,
    }
