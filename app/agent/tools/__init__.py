# -*- coding: utf-8 -*-
"""Agent 工具包（阶段4，提示词7）：5 个工具 + 注册表 + 执行上下文。

对外导出（agent_loop 使用）：
- ToolContext           工具执行上下文（含确认门硬约束状态）
- get_tool_schemas()    Function Calling 工具描述（传给 LLM）
- execute_tool()        执行工具 + 决策日志落库
"""
from __future__ import annotations

from .context import ToolContext
from .registry import execute_tool, get_tool_schemas

__all__ = ["ToolContext", "get_tool_schemas", "execute_tool"]
