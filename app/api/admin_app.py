# -*- coding: utf-8 -*-
"""选课申请管理（阶段4，提示词7）：教务管理员 API + 审核页面。

- API（Bearer/Cookie 鉴权，仅 admin）：
    GET  /api/admin/applications                 申请列表（可按状态筛选）
    POST /api/admin/applications/{no}/review     审核（approve/reject，reject 必填原因）
- 页面（Jinja2 服务端渲染，Cookie 鉴权）：
    GET /admin/applications  申请审核页
状态机：draft → student_confirmed → admin_confirmed → executed；可 rejected。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from ..models import User
from ..schemas import ReviewRequest
from ..security import optional_user, require_roles
from ..services.application_service import list_applications, review_by_admin
from ..templating import templates

router = APIRouter()


# ══════════ 管理员 API ══════════

@router.get("/api/admin/applications")
async def applications(status: str | None = Query(default=None),
                       user: User = Depends(require_roles("admin"))):
    """选课申请列表（时间倒序；?status= 筛选状态机节点）。"""
    items = await list_applications(status=status)
    return {"total": len(items), "items": items}


@router.post("/api/admin/applications/{business_no}/review")
async def review(business_no: str, req: ReviewRequest,
                 user: User = Depends(require_roles("admin"))):
    """教务审核：approve=同意（→admin_confirmed）/ reject=驳回（须填原因）。

    制度 2.6/2.7：系统不自动批准选课，须教务管理员确认后方可执行。
    """
    result = await review_by_admin(business_no, user, req.action, req.note)
    action_cn = {"approve": "已同意", "reject": "已驳回",
                 "execute": "已标记执行完毕"}.get(req.action, req.action)
    return {"message": f"申请单 {business_no} {action_cn}，当前状态：{result['status']}",
            "application": result}


# ══════════ 页面（服务端渲染）══════════

@router.get("/admin/applications", include_in_schema=False)
async def applications_page(request: Request):
    """选课申请审核页：仅管理员（未登录/权限不足 → 跳转登录页）。"""
    user = await optional_user(request)
    if user is None or user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "admin_app.html", {"user": user})
