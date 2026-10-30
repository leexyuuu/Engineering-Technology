# -*- coding: utf-8 -*-
"""请求/响应模型与统一错误码（阶段3）。

约定：所有接口先返回"错误码 + 中文错误信息"，绝不静默失败。
- 流式开始【前】的错误 → HTTP 状态码 + {"code", "message"} JSON；
- 流式开始【后】的错误 → SSE error 事件 {"code", "message"}（见 chat_service）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorCode:
    """统一错误码表（code, HTTP 状态码, 默认中文信息）。"""
    BAD_REQUEST = ("40001", 400, "参数缺失或非法")
    SESSION_NOT_FOUND = ("40401", 404, "会话不存在")
    DOC_NOT_FOUND = ("40402", 404, "文档不存在")
    APPLICATION_NOT_FOUND = ("40403", 404, "选课申请不存在")
    RATE_LIMITED = ("42901", 429, "请求过于频繁，请稍后再试")
    UNAUTHORIZED = ("40101", 401, "未登录或登录已过期，请重新登录")
    AUTH_FAILED = ("40102", 401, "用户名或密码错误")
    FORBIDDEN = ("40301", 403, "无权访问该功能")
    APPLICATION_STATE_ERROR = ("40901", 409, "申请当前状态不允许该操作")
    RETRIEVAL_ERROR = ("50001", 500, "检索服务异常，请稍后重试")
    LLM_ERROR = ("50301", 500, "回答生成失败（LLM 调用超时或出错），请稍后重试")
    LLM_CONFIG_ERROR = ("50302", 500, "LLM 供应商配置错误，请联系管理员")
    TOOL_EXECUTE_ERROR = ("50003", 500, "工具执行异常，请稍后重试")


class ApiError(Exception):
    """业务异常：携带 (错误码, HTTP 状态码, 中文信息)，由全局异常处理器统一返回。"""

    def __init__(self, code_tuple: tuple, message: str | None = None):
        self.code, self.status_code, default_msg = code_tuple
        self.message = message or default_msg
        super().__init__(self.message)


class ChatRequest(BaseModel):
    """POST /api/chat 请求体。"""
    session_id: str | None = Field(default=None, description="会话 id；为空则新建会话")
    question: str = Field(min_length=1, max_length=500, description="学生问题")


class LoginRequest(BaseModel):
    """POST /api/auth/login 请求体。"""
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


# ══════════ 阶段4（提示词7）：确认门与申请审核请求模型 ══════════

class ConfirmRequest(BaseModel):
    """POST /api/chat/confirm 请求体：学生对 draft 申请单的确认/撤销。"""
    session_id: str = Field(min_length=1, max_length=36, description="产生申请的会话 id")
    business_no: str = Field(min_length=1, max_length=32, description="申请单业务编号")
    action: str = Field(description="confirm=确认提交 / reject=撤销申请")


class ReviewRequest(BaseModel):
    """POST /api/admin/applications/{business_no}/review 请求体：教务管理员审核。"""
    action: str = Field(description="approve=同意（进入待执行）/ reject=驳回（须填原因）")
    note: str = Field(default="", max_length=200, description="人工改动说明或驳回原因（驳回必填）")
