# -*- coding: utf-8 -*-
"""安全模块（阶段3）：密码哈希、JWT 签发/校验、接口级权限依赖。

设计要点：
- 密码哈希用标准库 PBKDF2-HMAC-SHA256（10 万轮 + 随机盐），零第三方依赖；
- JWT 用 PyJWT（HS256）：payload 含 sub(用户id) / role / username / exp；
- 凭证双通道：Authorization: Bearer 头（前端 API）+ HttpOnly Cookie（管理页导航）；
- get_current_user / require_roles 是 FastAPI 依赖，接口级权限校验的统一入口。
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Request
from sqlalchemy import func, select

from .config import settings
from .db import AsyncSessionLocal
from .models import User
from .schemas import ApiError, ErrorCode

_ITERATIONS = 100_000   # PBKDF2 迭代次数

# 演示账号（仅开发/验收用；生产环境必须改用正式账号体系）
DEMO_USERS = [
    ("student1", "123456", "student", "张同学"),
    ("teacher1", "123456", "teacher", "李老师"),
    ("admin1", "123456", "admin", "王管理员"),
]


# ── 密码哈希 ──
def hash_password(password: str) -> str:
    """生成 '盐$哈希' 格式的密码串。"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码（常数时间比较，防时序攻击）。"""
    try:
        salt, hexdk = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return secrets.compare_digest(dk.hex(), hexdk)


# ── JWT ──
def create_token(user: User) -> str:
    """签发 JWT（HS256，有效期见 settings.jwt_expire_hours）。"""
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode_token(token: str) -> dict:
    """校验并解码 JWT；无效/过期 → 40101。"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise ApiError(ErrorCode.UNAUTHORIZED)   # noqa: B904


def _token_from_request(request: Request) -> str | None:
    """凭证双通道：优先 Bearer 头，其次 Cookie（管理页导航场景）。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")


# ── FastAPI 依赖（接口级权限校验入口）──
async def get_current_user(request: Request) -> User:
    """解析当前登录用户；未登录/凭证无效 → 40101。"""
    token = _token_from_request(request)
    if not token:
        raise ApiError(ErrorCode.UNAUTHORIZED)
    payload = _decode_token(token)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise ApiError(ErrorCode.UNAUTHORIZED)
    return user


async def optional_user(request: Request) -> User | None:
    """页面路由用：未登录返回 None（由页面决定跳转登录）。"""
    try:
        return await get_current_user(request)
    except ApiError:
        return None


def require_roles(*roles: str):
    """接口级权限依赖工厂。

    用法：
        user: User = Depends(require_roles("admin"))                # 仅管理员
        user: User = Depends(require_roles("student", "teacher"))    # 学生或教师
    """
    async def _dep(request: Request) -> User:
        user = await get_current_user(request)
        if roles and user.role not in roles:
            raise ApiError(ErrorCode.FORBIDDEN)
        return user
    return _dep


# ── 演示账号种子 ──
async def seed_demo_users() -> None:
    """首次启动时写入三角色演示账号（已存在则跳过）。"""
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(User))).scalar()
        if count:
            return
        for username, password, role, real_name in DEMO_USERS:
            db.add(User(username=username, password_hash=hash_password(password),
                        role=role, real_name=real_name))
        await db.commit()
