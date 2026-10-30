# -*- coding: utf-8 -*-
"""异步数据库引擎与会话工厂（SQLite + SQLAlchemy 2.0 async，可平滑切换 PostgreSQL）。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

# echo=False：不打印 SQL 日志
engine = create_async_engine(settings.db_url, echo=False)
# expire_on_commit=False：提交后对象属性仍可访问，便于跨会话使用
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


async def init_db() -> None:
    """启动时自动建表（阶段2：conversations / messages；阶段3 追加管理员相关表）。"""
    from . import models  # noqa: F401 —— 导入以触发模型注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
