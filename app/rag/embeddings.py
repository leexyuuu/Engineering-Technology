# -*- coding: utf-8 -*-
"""向量化：供应商可配置（阶段1 起核心复用模块，阶段2 异步化）。

- openai_compatible：任意 OpenAI 兼容 /embeddings 端点（生产默认，分批 64 条）；
- local_hash：离线验证用的哈希词袋嵌入（无语义能力，仅保证管线离线可跑，
  此时检索质量主要依赖 BM25；生产必须切换到 API 嵌入）。
两种供应商统一做 L2 归一化 → 与 FAISS IndexFlatIP 组合即为余弦相似度。
"""
from __future__ import annotations

import hashlib

import jieba
import numpy as np

from ..config import settings


async def embed_texts(texts: list[str]) -> np.ndarray:
    """一批文本 → (n, dim) 的 L2 归一化 float32 矩阵。"""
    if settings.embedding_provider == "openai_compatible":
        from openai import AsyncOpenAI   # 延迟导入：mock/local 模式不依赖网络
        client = AsyncOpenAI(base_url=settings.embedding_base_url or None,
                             api_key=settings.embedding_api_key,
                             timeout=settings.llm_timeout)
        vecs: list[list[float]] = []
        for i in range(0, len(texts), 64):   # 分批请求，避免单次超长
            resp = await client.embeddings.create(model=settings.embedding_model,
                                                  input=texts[i:i + 64])
            vecs.extend(d.embedding for d in resp.data)
        mat = np.asarray(vecs, dtype="float32")
    else:
        # local_hash：分词哈希到固定维度并计数 → 归一化词袋向量（离线冒烟用）
        dim = 256
        mat = np.zeros((len(texts), dim), dtype="float32")
        for row, t in enumerate(texts):
            for tok in jieba.lcut(t):
                idx = int.from_bytes(
                    hashlib.md5(tok.encode("utf-8")).digest()[:4], "little") % dim
                mat[row, idx] += 1.0

    # L2 归一化：让内积（IP）等价于余弦相似度
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype("float32")
