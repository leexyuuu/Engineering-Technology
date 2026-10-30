# -*- coding: utf-8 -*-
"""入口层（阶段4，提示词7）：POST /api/chat + POST /api/chat/confirm。

- POST /api/chat：SSE 流式问答（Agent 循环：工具调用/直答/确认门）；
- POST /api/chat/confirm：学生对 draft 选课申请的确认/撤销（确认门后半段）；
- 限流（42901）与会话校验（40401）在流式开始前完成，返回干净的 HTTP 错误。
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ..config import settings
from ..models import User
from ..schemas import (ApiError, ChatRequest, ConfirmRequest, ErrorCode)
from ..security import get_current_user
from ..services.application_service import confirm_by_student
from ..services.chat_service import chat_service

router = APIRouter()

# ── 简版限流：内存滑动窗口（按客户端 IP，每分钟 N 次；上线前替换为 Redis）──
_HITS: dict[str, deque] = defaultdict(deque)
_WINDOW = 60.0


def _allow(ip: str) -> bool:
    """滑动窗口判流：窗口内请求数超限则拒绝。"""
    now = time.time()
    q = _HITS[ip]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= settings.rate_limit_per_minute:
        return False
    q.append(now)
    return True


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request,
               user: User = Depends(get_current_user)):
    # 1) 限流（42901）
    ip = request.client.host if request.client else "unknown"
    if not _allow(ip):
        raise ApiError(ErrorCode.RATE_LIMITED)

    # 2) 会话校验（40401）——必须在响应开始前完成，才能返回干净的 HTTP 错误
    conv = await chat_service.get_or_create_session(req.session_id, req.question, user)

    # 3) SSE 流式响应（Agent 循环；user 供工具上下文取学籍等身份信息）
    return EventSourceResponse(chat_service.stream(conv, req.question, user))


@router.post("/api/chat/confirm")
async def confirm(req: ConfirmRequest, user: User = Depends(get_current_user)):
    """确认门后半段：学生确认（draft→student_confirmed）或撤销（→rejected）。

    business_no 与 session_id 来自 SSE confirm_required 事件；归属与状态机
    校验在 application_service 内完成（40403 / 40301 / 40901）。
    """
    result = await confirm_by_student(req.session_id, req.business_no,
                                      user, req.action)
    action_cn = "已确认提交" if req.action == "confirm" else "已撤销"
    return {"message": f"申请单 {req.business_no} {action_cn}，"
                       f"当前状态：{result['status']}", "application": result}
