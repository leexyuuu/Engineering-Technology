# -*- coding: utf-8 -*-
"""聊天服务（阶段4 改造，提示词7）：Agent 执行循环编排 + 会话/消息持久化。

阶段4 变化：
- 原"检索 → 装配 → LLM 直答"升级为"检索 → Agent 循环（工具调用 + 决策日志
  + 确认门）→ 最终回答"；
- SSE 事件协议扩展：新增 tool（工具步骤）、confirm_required（选课申请确认
  卡片）事件；普通制度问答路径行为与阶段 2/3 完全一致（兼容存量功能）。

一次问答的事件序列（与前端约定一致）：
    status(thinking) → tool(×N，每轮工具) → [confirm_required] → message(×N)
    → citations → done {tools_used}
任一环节失败 → error 事件（错误码 + 中文信息），绝不静默失败。
"""
from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from sqlalchemy import select

from ..agent.agent_loop import run_agent_loop
from ..agent.tools import ToolContext
from ..agent.tools.mock_data import USER_STUDENT_MAP
from ..config import settings
from ..db import AsyncSessionLocal
from ..models import Conversation, Message, User
from ..schemas import ApiError, ErrorCode
from .prompt_service import get_active_prompt
from .retrieval_service import retrieval


def _sse(event: str, data: dict | list) -> dict:
    """把事件包装成 sse-starlette 需要的 {event, data(json字符串)} 结构。"""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


class ChatService:
    """编排一次问答：检索 → Agent 循环（工具/直答）→ 落库。"""

    # ── 会话管理 ──
    async def get_or_create_session(self, session_id: str | None,
                                    question: str, user: User) -> Conversation:
        """取会话；session_id 为空则新建（回填 user_id）。不存在 → 40401。"""
        async with AsyncSessionLocal() as db:
            if session_id:
                conv = (await db.execute(
                    select(Conversation).where(Conversation.session_id == session_id)
                )).scalar_one_or_none()
                if conv is None:
                    raise ApiError(ErrorCode.SESSION_NOT_FOUND)
                return conv
            conv = Conversation(session_id=str(uuid.uuid4()),
                                user_id=user.id, title=question[:30])
            db.add(conv)
            await db.commit()
            await db.refresh(conv)
            return conv

    # ── 历史与落库 ──
    async def _load_history(self, conversation_id: int) -> list[dict[str, str]]:
        """取最近 history_rounds 轮（=12 条）消息，时间正序返回。"""
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id.desc())
                .limit(settings.history_rounds * 2)
            )).scalars().all()
        return [{"role": m.role, "content": m.content} for m in reversed(rows)]

    async def _save_message(self, conversation_id: int, role: str, content: str,
                            citations: list | None = None) -> int:
        """落库一条消息，返回消息 id。"""
        async with AsyncSessionLocal() as db:
            msg = Message(conversation_id=conversation_id, role=role,
                          content=content, citations=citations)
            db.add(msg)
            await db.commit()
            return msg.id

    # ── 流式主流程（Agent 编排）──
    async def stream(self, conv: Conversation, question: str,
                     user: User) -> AsyncIterator[dict]:
        """产出 SSE 事件流（会话与用户已在入口层校验/创建完毕）。"""
        t0 = time.perf_counter()

        # 1) 状态事件：前端显示"正在思考…"
        yield _sse("status", {"phase": "thinking", "text": "正在思考你的问题…"})

        # 2) 背景检索（两用）：无工具意图时的直答上下文 + citations 来源
        #    （Agent 需要制度依据时会再调 search_selection_rules 工具自主检索）
        try:
            hits = await retrieval.retrieve(question)
        except Exception as exc:   # noqa: BLE001
            yield _sse("error", {"code": ErrorCode.RETRIEVAL_ERROR[0],
                                 "message": f"{ErrorCode.RETRIEVAL_ERROR[2]}（{exc}）"})
            return

        # 3) 装配输入：DB 模板（热生效，含 Agent 工具约束版） + 历史
        history = await self._load_history(conv.id)
        system_prompt = await get_active_prompt()

        # 4) 落库用户消息（检索成功后才落库，避免失败请求污染历史）
        await self._save_message(conv.id, "user", question)

        # 5) Agent 执行循环：工具调用 / 直答 / 确认门（结果经 result_box 带回）
        ctx = ToolContext(
            conversation_id=conv.id, user_id=user.id,
            username=user.username, role=user.role,
            student_no=USER_STUDENT_MAP.get(user.username, ""),   # 演示学号映射
        )
        result_box: dict = {}
        async for event in run_agent_loop(conv.id, question, hits, history,
                                          system_prompt, ctx, result_box):
            yield event

        # 6) 引用事件 + 落库助手消息（引用来源随消息持久化，供审计）
        yield _sse("citations", result_box.get("citations", []))
        answer = result_box.get("answer", "")
        if answer:
            msg_id = await self._save_message(conv.id, "assistant", answer,
                                              result_box.get("citations") or None)
        else:
            msg_id = 0   # error 事件已发出，不再落库助手消息

        # 7) 收尾事件：会话 id 供续聊；tools_used 供前端/评测分析调用轨迹
        yield _sse("done", {
            "session_id": conv.session_id, "message_id": msg_id,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "tools_used": result_box.get("tools_used", []),
        })


# 模块级单例
chat_service = ChatService()
