# -*- coding: utf-8 -*-
"""知识库管理（阶段3批1）：管理员 API + 服务端渲染页面。

- API（Bearer/Cookie 鉴权，仅 admin）：
    POST   /api/admin/kb/upload          上传 md/pdf → 切片 → 向量化入库（立即生效）
    GET    /api/admin/kb/documents       活跃文档列表
    DELETE /api/admin/kb/documents/{id}  软删除 + 重建索引
- 页面（Jinja2 服务端渲染，Cookie 鉴权，未登录跳转 /login）：
    GET /login    登录页（三角色）
    GET /admin/kb 知识库管理页
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import RedirectResponse

from ..models import User
from ..security import optional_user, require_roles
from ..services.kb_service import kb_service
from ..templating import templates

router = APIRouter()


# ══════════ 管理员 API（接口级权限校验：仅 admin）══════════

@router.post("/api/admin/kb/upload")
async def upload(file: UploadFile = File(...),
                 user: User = Depends(require_roles("admin"))):
    """上传文档：抽取文本 → 500 字切片 → 向量化入库 → 重建索引。"""
    data = await file.read()
    result = await kb_service.upload(file.filename, data, uploader=user)
    return {"message": f"上传成功：切片 {result['chunk_count']} 段，"
                       f"知识库当前共 {result['index_total']} 段", **result}


@router.get("/api/admin/kb/documents")
async def list_documents(user: User = Depends(require_roles("admin"))):
    """活跃文档列表（含版本、切片数、上传时间）。"""
    docs = await kb_service.list_documents()
    return {"total": len(docs), "documents": docs}


@router.delete("/api/admin/kb/documents/{doc_id}")
async def delete_document(doc_id: int, user: User = Depends(require_roles("admin"))):
    """软删除文档并重建索引（立即从检索中移除）。"""
    await kb_service.delete(doc_id)
    return {"message": "文档已删除，索引已重建"}


# ══════════ 页面（服务端渲染）══════════

@router.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """登录页：三角色统一入口。"""
    return templates.TemplateResponse(request, "login.html")


@router.get("/admin/kb", include_in_schema=False)
async def kb_page(request: Request):
    """知识库管理页：仅管理员（未登录/权限不足 → 跳转登录页）。"""
    user = await optional_user(request)
    if user is None or user.role != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "admin_kb.html", {"user": user})
