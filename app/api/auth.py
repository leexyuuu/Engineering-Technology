# -*- coding: utf-8 -*-
"""认证接口（阶段3）：登录签发 JWT + 当前用户信息。

登录成功同时做两件事（凭证双通道）：
- 响应体返回 token（前端存 localStorage，供 API 调用带 Bearer 头）；
- 设置 HttpOnly Cookie（管理页浏览器导航自动携带）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from ..config import settings
from ..db import AsyncSessionLocal
from ..models import User
from ..schemas import ApiError, ErrorCode, LoginRequest
from ..security import create_token, get_current_user, verify_password

router = APIRouter()


@router.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    """账号密码登录 → 签发 JWT（24h，含 role claim）。"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.username == req.username))).scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise ApiError(ErrorCode.AUTH_FAILED)
    if not user.is_active:
        raise ApiError(ErrorCode.AUTH_FAILED, "账号已停用，请联系管理员")

    token = create_token(user)
    # HttpOnly Cookie：管理页导航场景自动携带（SameSite=Lax 防基本 CSRF）
    response.set_cookie("token", token, max_age=settings.jwt_expire_hours * 3600,
                        httponly=True, samesite="lax")
    return {"token": token, "role": user.role,
            "username": user.username, "real_name": user.real_name}


@router.get("/api/auth/me")
async def me(user: User = Depends(get_current_user)):
    """当前登录用户信息（前端启动时校验登录态）。"""
    return {"id": user.id, "username": user.username,
            "role": user.role, "real_name": user.real_name}
