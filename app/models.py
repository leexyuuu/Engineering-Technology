# -*- coding: utf-8 -*-
"""ORM 模型（阶段4）：10 张表。

阶段2：conversations / messages（会话与消息，含引用来源、违规标记字段）
阶段3新增：
- users            三角色账号（student / teacher / admin）
- documents        教务制度文档（版本/生效日期/适用范围，软删除保留审计痕迹）
- doc_chunks       文档切片（正文与章节；向量存 FAISS 文件，BM25 内存重建）
- prompt_templates 系统提示词模板（管理员编辑，保存即生效，不写死代码）
阶段4新增（提示词7：Agent 执行循环）：
- agent_decision_logs   Agent 每轮工具决策日志（轮次/工具名/参数/耗时/结果摘要）
- selection_applications 选课申请单（状态机 + 审计五要素，见 create 工具）
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    """用户表：三角色。密码为 PBKDF2-HMAC-SHA256 哈希（见 security.py）。"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))              # student / teacher / admin
    real_name: Mapped[str] = mapped_column(String(50), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Conversation(Base):
    """会话表：一次持续的多轮对话（user_id 由 JWT 回填）。"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)           # JWT 用户 id
    title: Mapped[str] = mapped_column(String(120), default="")                  # 首问截断
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)


class Message(Base):
    """消息表：user / assistant 消息与引用来源（审计"事实引用"要素落位）。"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))                 # user / assistant
    content: Mapped[str] = mapped_column(Text)                    # 消息正文
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 引用来源列表
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)     # 审计页：疑似违规标记
    flag_reason: Mapped[str] = mapped_column(String(200), default="")    # 审计页：标记原因
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Document(Base):
    """教务制度文档表：知识库管理页维护（上传/删除）。"""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    doc_type: Mapped[str] = mapped_column(String(30), default="综合")      # 排课规则/选课规则/学分课表标准/综合
    version: Mapped[str] = mapped_column(String(20), default="v1")        # 版本（审计"资料版本"要素）
    effective_date: Mapped[str] = mapped_column(String(20), default="")   # 生效日期
    applicable_scope: Mapped[str] = mapped_column(String(200), default="全院")
    status: Mapped[str] = mapped_column(String(16), default="active")     # active / deleted
    uploader_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)


class DocChunk(Base):
    """文档切片表：切片正文与章节（id 与 FAISS 内部向量编号在重建时对齐）。"""
    __tablename__ = "doc_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)              # 文档内片段号（从 1 开始）
    heading: Mapped[str] = mapped_column(String(200), default="")  # 所属章节（引用展示）
    content: Mapped[str] = mapped_column(Text)                    # 切片正文
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PromptTemplate(Base):
    """系统提示词模板：管理员后台编辑，保存即生效（chat 每次请求实时读取）。"""
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="默认模板")
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)


class AgentDecisionLog(Base):
    """Agent 决策日志（阶段4，提示词7）：每轮工具调用的完整轨迹。

    用途：阶段5 评测时分析"模型是否按约定的调用顺序使用工具"（如是否跳过
    validate_eligibility）、各工具耗时分布、结果摘要供人工抽检。
    一轮 = 一次工具调用（或最终作答，tool_name 记为 __final_answer__）。
    """
    __tablename__ = "agent_decision_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True)          # 归属会话（关联问题）
    round: Mapped[int] = mapped_column(Integer)               # Agent 循环轮次（从 1 开始）
    tool_name: Mapped[str] = mapped_column(String(64))        # 工具名（或 __final_answer__）
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)     # 工具入参
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)         # 工具执行耗时
    result_summary: Mapped[str] = mapped_column(Text, default="")        # 结果摘要（截断）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SelectionApplication(Base):
    """选课申请单（阶段4，提示词7）：状态机 + 审计五要素落位。

    状态机（业务调研 f05/f33：接口只读不代选、申请须学生确认+教务执行）：
        draft（Agent 生成，待学生确认）
          → student_confirmed（学生确认，待教务审核）
          → admin_confirmed（教务管理员确认，待教务系统执行）
          → executed（已在教务系统执行，终态）
        任一非终态可 → rejected（学生撤销 / 教务驳回，需备注原因）。

    审计五要素（f45）字段对应：
        业务编号 → business_no；资料版本 → rule_refs 中的制度/课表版本；
        事实引用 → eligibility_result（校验结论与依据条文）；人工改动 → admin_note；
        签核人 → admin_id（确认的管理员）。
    """
    __tablename__ = "selection_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # 业务编号 XK+日期+序号
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True)          # 产生申请的会话（可溯源）
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True)                  # 申请学生（登录账号）
    student_no: Mapped[str] = mapped_column(String(20))      # 学号（展示用）
    student_name: Mapped[str] = mapped_column(String(50), default="")
    semester: Mapped[str] = mapped_column(String(20))        # 选课学期（如 2026-2027-1）
    course_code: Mapped[str] = mapped_column(String(20))     # 课程代码
    course_name: Mapped[str] = mapped_column(String(100))    # 课程名称
    credits: Mapped[int] = mapped_column(Integer, default=0) # 课程学分
    eligibility_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 资格校验结论
    rule_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)           # 依据条文与版本
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # 状态机
    admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)          # 签核管理员
    admin_note: Mapped[str] = mapped_column(String(200), default="")              # 人工改动/驳回原因
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)
