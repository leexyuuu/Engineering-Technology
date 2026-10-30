# -*- coding: utf-8 -*-
"""应用配置（阶段3）：供应商可替换、鉴权、路径与限流参数，全部可用 .env / 环境变量覆盖。

默认值保证"开箱即跑"（mock LLM + 本地哈希嵌入，离线可用）；
接入真实供应商时复制 .env.example 为 .env 修改即可，无需改代码。
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 = app/ 的上一级
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ── LLM 供应商（问答生成，可替换）──
    llm_provider: str = "mock"            # mock=离线冒烟 / openai_compatible=真实调用
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: float = 60.0

    # ── Embedding 供应商（向量化，可替换）──
    embedding_provider: str = "local_hash"   # local_hash=离线验证 / openai_compatible=真实
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    # ── 检索与会话 ──
    chunk_size: int = 500       # 制度文档切片长度（字符）
    top_k: int = 3              # 混合检索返回条数
    history_rounds: int = 6     # 携带最近 6 轮（=12 条消息）对话历史

    # ── JWT 鉴权（阶段3）──
    jwt_secret: str = "dev-secret-生产环境务必修改"   # 签名密钥（生产必须改）
    jwt_expire_hours: int = 24                        # token 有效期

    # ── 限流（简版内存滑动窗口；上线前替换为 Redis）──
    rate_limit_per_minute: int = 20

    # ── 上传限制 ──
    max_upload_mb: int = 10      # 知识库文档上传大小上限

    # ── 路径与数据库（SQLite 起步，保留切换 PostgreSQL 的能力）──
    docs_dir: Path = BASE_DIR / "data" / "docs"       # 种子制度文档（首次启动自动入库）
    uploads_dir: Path = BASE_DIR / "data" / "uploads"  # 管理员上传的文档原件（审计留存）
    faiss_dir: Path = BASE_DIR / "data" / "faiss"     # 向量索引持久化目录
    db_url: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
