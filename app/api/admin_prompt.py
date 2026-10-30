# -*- coding: utf-8 -*-
"""提示词模板管理（阶段3批2）：管理员 API + 服务端渲染页面。

- GET /api/admin/prompt  读取当前生效的系统提示词；
- PUT /api/admin/prompt  更新（存数据库，保存即对问答生效——不写死在代码里）；
- GET /admin/prompt      管理页（仅管理员，未登录跳转 /login）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..models import User
from ..security import optional_user, require_roles
from ..services import prompt_service
from ..templating import templates

router = APIRouter()


class PromptUpdate(BaseModel):
    """PUT /api/admin/prompt 请求体。"""
    content: str = Field(min_length=10, max_length=4000, description="系统提示词内容")


@router.get("/api/admin/prompt")
async def get_prompt(user: User = Depends(require_roles("admin"))):
    """读取当前生效的系统提示词模板。"""
    tpl = await prompt_service.get_active_template()
    return {
        "name": tpl.name if tpl else "默认模板",
        "content": tpl.content if tpl else "",
        "updated_at": tpl.updated_at.strftime("%Y-%m-%d %H:%M:%S") if tpl else "",
        "updated_by": tpl.updated_by if tpl else None,
    }


@router.put("/api/admin/prompt")
async def update_prompt(req: PromptUpdate, user: User = Depends(require_roles("admin"))):
    """更新系统提示词（保存即生效，无需重启）。"""
    await prompt_service.update_prompt(req.content, user.id)
    return {"message": "提示词已保存并立即对问答生效"}


@router.get("/admin/prompt", include_in_schema=False)
async def prompt_page(request: Request):
    """提示词模板管理页：仅管理员。"""
    user = await optional_user(request)
    if user is None or user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "admin_prompt.html", {"user": user})
