# -*- coding: utf-8 -*-
"""选课申请服务（阶段4，提示词7）：申请单状态机流转 + 查询。

状态机（见 models.SelectionApplication 文档）：
    draft --学生确认--> student_confirmed --教务同意--> admin_confirmed --执行--> executed
      └────────── 任一非终态可 rejected（学生撤销 / 教务驳回，须备注原因）──┘

安全约束：
- 学生确认/撤销：只能操作【本人】在【指定会话】产生的 draft 申请（防越权）；
- 教务审核：仅 admin 角色，只能操作 student_confirmed 状态（跳状态一律 40901）；
- 驳回必填原因（审计"人工改动"要素，f45）。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select

from ..db import AsyncSessionLocal
from ..models import SelectionApplication, User
from ..schemas import ApiError, ErrorCode

# 状态机合法流转表：当前状态 → {动作: 目标状态}
TRANSITIONS: dict[str, dict[str, str]] = {
    "draft": {"confirm": "student_confirmed", "reject": "rejected"},
    "student_confirmed": {"approve": "admin_confirmed", "reject": "rejected"},
    "admin_confirmed": {"execute": "executed"},
    # executed / rejected 为终态
}


async def confirm_by_student(session_id: str, business_no: str,
                             user: User, action: str) -> dict[str, Any]:
    """学生确认（confirm）或撤销（reject）draft 申请 → student_confirmed / rejected。"""
    if action not in ("confirm", "reject"):
        raise ApiError(ErrorCode.BAD_REQUEST, "action 仅支持 confirm / reject")

    async with AsyncSessionLocal() as db:
        app = (await db.execute(
            select(SelectionApplication)
            .where(SelectionApplication.business_no == business_no)
        )).scalar_one_or_none()
        if app is None:
            raise ApiError(ErrorCode.APPLICATION_NOT_FOUND)

        # 归属校验：本人的申请 + 本人会话（会话 id 来自 confirm_required 事件）
        if app.user_id != user.id:
            raise ApiError(ErrorCode.FORBIDDEN, "只能操作本人的选课申请")
        from ..models import Conversation
        conv = await db.get(Conversation, app.conversation_id)
        if conv is None or conv.session_id != session_id:
            raise ApiError(ErrorCode.BAD_REQUEST, "会话与申请单不匹配，请刷新后重试")

        # 状态机校验 + 流转
        target = TRANSITIONS.get(app.status, {}).get(action)
        if target is None:
            raise ApiError(ErrorCode.APPLICATION_STATE_ERROR,
                           f"申请当前状态为 {app.status}，不允许执行 {action}")
        app.status = target
        if action == "reject":
            app.admin_note = "学生本人撤销"
        await db.commit()
        return _view(app)


async def review_by_admin(business_no: str, admin: User,
                          action: str, note: str) -> dict[str, Any]:
    """教务管理员审核 student_confirmed 申请 → admin_confirmed / rejected。"""
    if action not in ("approve", "reject", "execute"):
        raise ApiError(ErrorCode.BAD_REQUEST,
                       "action 仅支持 approve / reject / execute")
    if action == "reject" and not note.strip():
        raise ApiError(ErrorCode.BAD_REQUEST, "驳回必须填写原因（审计要求）")

    async with AsyncSessionLocal() as db:
        app = (await db.execute(
            select(SelectionApplication)
            .where(SelectionApplication.business_no == business_no)
        )).scalar_one_or_none()
        if app is None:
            raise ApiError(ErrorCode.APPLICATION_NOT_FOUND)

        target = TRANSITIONS.get(app.status, {}).get(action)
        if target is None:
            raise ApiError(ErrorCode.APPLICATION_STATE_ERROR,
                           f"申请当前状态为 {app.status}，不允许执行 {action}")
        app.status = target
        if action == "reject":
            app.admin_note = note.strip()[:200]      # 人工改动说明（f45）
        app.admin_id = admin.id                      # 签核人（f45）
        await db.commit()
        return _view(app)


async def list_applications(status: str | None = None,
                            limit: int = 100) -> list[dict[str, Any]]:
    """申请列表（管理页）：可按状态筛选，时间倒序。"""
    async with AsyncSessionLocal() as db:
        stmt = select(SelectionApplication).order_by(
            SelectionApplication.id.desc()).limit(limit)
        if status:
            stmt = stmt.where(SelectionApplication.status == status)
        rows = (await db.execute(stmt)).scalars().all()
        return [_view(a) for a in rows]


def _view(a: SelectionApplication) -> dict[str, Any]:
    """申请单对外视图（JSON 安全）。"""
    return {
        "id": a.id, "business_no": a.business_no, "status": a.status,
        "student_no": a.student_no, "student_name": a.student_name,
        "semester": a.semester, "course_code": a.course_code,
        "course_name": a.course_name, "credits": a.credits,
        "eligibility": a.eligibility_result, "rule_refs": a.rule_refs,
        "admin_note": a.admin_note,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
        "updated_at": a.updated_at.strftime("%Y-%m-%d %H:%M:%S") if a.updated_at else "",
    }
