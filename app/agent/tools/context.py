# -*- coding: utf-8 -*-
"""工具执行上下文（阶段4，提示词7）：ToolContext。

作用：
1) 把"当前请求"的身份与会话信息传递给每个工具（工具不直接依赖 FastAPI）；
2) 携带【确认门硬约束】的状态：validated_courses 记录本会话（本次请求内）
   已通过 validate_eligibility 的课程代码 —— create_selection_application
   执行前强制检查该集合，模型无法通过提示词注入绕过（代码层硬约束）；
3) validated_results 缓存校验结论，建申请时直接引用（保证申请单上的
   资格结论与校验结果一致，不二次计算）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolContext:
    """一次 /api/chat 请求内的工具共享上下文（请求级生命周期）。"""

    conversation_id: int                       # 当前会话 id（决策日志/申请单归属）
    user_id: int                              # 登录用户 id
    username: str                             # 登录名（映射演示学号）
    role: str                                 # student / teacher / admin
    student_no: str = ""                      # 学号（无学籍角色为空串）

    # ── 确认门状态（硬约束依据）──
    validated_courses: set[str] = field(default_factory=set)     # 已通过资格校验的课程代码
    validated_results: dict[str, dict[str, Any]] = field(default_factory=dict)  # 校验结论缓存
    pending_application: dict[str, Any] | None = None            # create 成功的申请单（供确认事件）
