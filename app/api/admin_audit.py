# -*- coding: utf-8 -*-
"""对话审计（阶段3批2）：管理员 API + 服务端渲染页面。

- GET /api/admin/audit/messages            分页查询（角色/起止日期/关键词/仅看已标记）；
- PUT /api/admin/audit/messages/{id}/flag  标记/取消疑似违规（含原因）；
- GET /admin/audit                         审计页（仅管理员）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..models import User
from ..security import optional_user, require_roles
from ..services.audit_service import audit_service
from ..templating import templates

router = APIRouter()


class FlagRequest(BaseModel):
    """标记疑似违规请求体。"""
    flagged: bool = Field(description="True=标记 / False=取消")
    reason: str = Field(default="", max_length=200, description="标记原因（标记时必填）")


@router.get("/api/admin/audit/messages")
async def list_messages(
    role: str | None = Query(default=None, description="按用户角色筛选：student/teacher/admin"),
    start: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    end: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    keyword: str | None = Query(default=None, max_length=50, description="内容关键词"),
    flagged: bool = Query(default=False, description="仅看已标记的疑似违规消息"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_roles("admin")),
):
    """分页查询对话记录（新消息在前）。"""
    return await audit_service.query_messages(
        role=role, start=start, end=end, keyword=keyword,
        flagged_only=flagged, page=page, page_size=page_size)


@router.put("/api/admin/audit/messages/{message_id}/flag")
async def flag_message(message_id: int, req: FlagRequest,
                       user: User = Depends(require_roles("admin"))):
    """标记/取消疑似违规（如试图绕过选课资格的问答）。"""
    await audit_service.flag_message(message_id, req.flagged, req.reason)
    return {"message": "已标记疑似违规" if req.flagged else "已取消标记"}


@router.get("/admin/audit", include_in_schema=False)
async def audit_page(request: Request):
    """对话审计页：仅管理员。"""
    user = await optional_user(request)
    if user is None or user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "admin_audit.html", {"user": user})
