# -*- coding: utf-8 -*-
"""对话审计服务（阶段3批2）：按角色/时间/关键词筛选 + 疑似违规标记。

- query_messages：messages ⨝ conversations ⨝ users 联查，支持
  角色 / 起止日期 / 关键词 / 仅看已标记 四类筛选 + 分页；
- flag_message：标记/取消"疑似违规"（如试图绕过选课资格的问答），须填原因。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, func, select

from ..db import AsyncSessionLocal
from ..models import Conversation, Message, User
from ..schemas import ApiError, ErrorCode

CONTENT_PREVIEW = 120   # 列表内容预览长度


def _parse_date(s: str | None, field: str) -> datetime | None:
    """解析 YYYY-MM-DD 日期参数；格式错误 → 40001。"""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError as exc:
        raise ApiError(ErrorCode.BAD_REQUEST, f"{field} 日期格式应为 YYYY-MM-DD") from exc


class AuditService:
    """对话审计（管理员功能的服务实现，页面与 API 共用）。"""

    async def query_messages(self, *, role: str | None = None, start: str | None = None,
                             end: str | None = None, keyword: str | None = None,
                             flagged_only: bool = False,
                             page: int = 1, page_size: int = 20) -> dict:
        """分页查询消息（含会话归属的用户信息），新消息在前。"""
        start_dt = _parse_date(start, "开始日期")
        end_dt = _parse_date(end, "结束日期")

        async with AsyncSessionLocal() as db:
            # 基础联查：消息 ← 会话 ← 用户（outerjoin：兼容阶段2遗留的无主会话）
            base = (select(Message, Conversation, User)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .outerjoin(User, Conversation.user_id == User.id))

            conds = []
            if role:
                conds.append(User.role == role)
            if start_dt is not None:
                conds.append(Message.created_at >= start_dt)
            if end_dt is not None:
                # 结束日期含当天：end 当天 00:00 + 1 天
                conds.append(Message.created_at < end_dt + timedelta(days=1))
            if keyword:
                conds.append(Message.content.like(f"%{keyword}%"))
            if flagged_only:
                conds.append(Message.is_flagged == True)   # noqa: E712
            if conds:
                base = base.where(and_(*conds))

            total = (await db.execute(
                select(func.count()).select_from(base.subquery()))).scalar()
            rows = (await db.execute(
                base.order_by(Message.id.desc())
                .offset((page - 1) * page_size).limit(page_size))).all()

        items = [{
            "id": msg.id,
            "session_id": conv.session_id,
            "username": user.username if user else "-",
            "real_name": user.real_name if user else "（未登录会话）",
            "user_role": user.role if user else "-",
            "msg_role": msg.role,                     # user=提问 / assistant=回答
            "content": msg.content[:CONTENT_PREVIEW] + ("…" if len(msg.content) > CONTENT_PREVIEW else ""),
            "citations_count": len(msg.citations or []),
            "is_flagged": msg.is_flagged,
            "flag_reason": msg.flag_reason,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        } for msg, conv, user in rows]
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    async def flag_message(self, message_id: int, flagged: bool, reason: str) -> None:
        """标记/取消疑似违规（标记须填原因，取消清空原因）。"""
        if flagged and not reason.strip():
            raise ApiError(ErrorCode.BAD_REQUEST, "标记疑似违规时必须填写原因")
        async with AsyncSessionLocal() as db:
            msg = await db.get(Message, message_id)
            if msg is None:
                raise ApiError(ErrorCode.DOC_NOT_FOUND, "消息不存在")
            msg.is_flagged = flagged
            msg.flag_reason = reason.strip() if flagged else ""
            await db.commit()


# 模块级单例
audit_service = AuditService()
