# -*- coding: utf-8 -*-
"""提示词模板服务（阶段3 起，阶段4 升级）：系统提示词存数据库，编辑后立即生效。

- init_default()：表为空时写入默认模板；表已有【旧版本默认值】（说明管理员
  从未自定义编辑过）时平滑升级为阶段4 的 Agent 版默认提示词——
  管理员自定义编辑过的内容永不覆盖；
- get_active_prompt()：chat 每次请求实时读取 —— 编辑保存即生效，无需重启；
- update_prompt()：管理页调用（保存即热生效）。
"""
from __future__ import annotations

from sqlalchemy import select

from ..agent.prompt_assembler import DEFAULT_SYSTEM_PROMPT, LEGACY_DEFAULT_PROMPTS
from ..db import AsyncSessionLocal
from ..models import PromptTemplate


async def init_default() -> None:
    """初始化/升级默认系统提示词模板（不覆盖管理员的自定义编辑）。"""
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(PromptTemplate).where(PromptTemplate.is_active == True)  # noqa: E712
        )).scalar_one_or_none()

        if existing is None:
            # 表为空：首次启动，写入当前默认模板
            db.add(PromptTemplate(name="默认模板", content=DEFAULT_SYSTEM_PROMPT,
                                  is_active=True))
            await db.commit()
            return

        # 平滑升级：内容仍是历史版本默认值（未被自定义编辑）→ 更新为新默认
        if existing.content in LEGACY_DEFAULT_PROMPTS:
            existing.content = DEFAULT_SYSTEM_PROMPT
            await db.commit()


async def get_active_template() -> PromptTemplate | None:
    """取当前生效的模板行（供管理页展示）。"""
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(PromptTemplate).where(PromptTemplate.is_active == True)  # noqa: E712
        )).scalar_one_or_none()


async def get_active_prompt() -> str:
    """取当前生效的系统提示词（chat 每请求调用：热生效）。"""
    tpl = await get_active_template()
    return tpl.content if tpl else ""


async def update_prompt(content: str, updated_by: int | None = None) -> PromptTemplate:
    """保存编辑后的提示词（保存即生效）。"""
    async with AsyncSessionLocal() as db:
        tpl = (await db.execute(
            select(PromptTemplate).where(PromptTemplate.is_active == True)  # noqa: E712
        )).scalar_one_or_none()
        if tpl is None:
            tpl = PromptTemplate(name="默认模板", content=content,
                                 is_active=True, updated_by=updated_by)
            db.add(tpl)
        else:
            tpl.content = content
            tpl.updated_by = updated_by
        await db.commit()
        await db.refresh(tpl)
        return tpl
