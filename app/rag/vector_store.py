# -*- coding: utf-8 -*-
"""FAISS 封装：建库 / 检索 / 持久化（阶段1 起核心复用模块）。

IndexFlatIP（内积）+ 归一化向量 = 余弦相似度。
阶段3 知识库管理复用 add/save 实现文档上传入库；
删除通过"从数据库重建索引"实现（见 retrieval_service.rebuild_from_db）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np


class FAISSStore:
    """FAISS 向量索引 + 切片元数据的统一封装。"""

    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)
        self.metas: list[dict[str, Any]] = []   # 第 i 条向量对应的切片元数据

    def add(self, embeddings: np.ndarray, metas: list[dict[str, Any]]) -> None:
        """批量写入向量与元数据（内部 id = 写入顺序 = 切片 id）。"""
        self.index.add(embeddings)
        self.metas.extend(metas)

    def search(self, qvec: np.ndarray, k: int = 10) -> list[tuple]:
        """按向量检索 top-k，返回 [(切片元数据, 相似度分数)]。"""
        if self.index.ntotal == 0:
            return []
        k = min(k, self.index.ntotal)
        scores, ids = self.index.search(np.asarray([qvec], dtype="float32"), k)
        return [(self.metas[i], float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]

    def save(self, folder: Path) -> None:
        """持久化：index.faiss（向量索引）+ chunks.json（切片元数据）。"""
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(folder / "index.faiss"))
        (folder / "chunks.json").write_text(
            json.dumps(self.metas, ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, folder: Path) -> "FAISSStore":
        """从磁盘加载索引与元数据；BM25 侧用同一份 chunks.json 重建。"""
        index = faiss.read_index(str(folder / "index.faiss"))
        metas = json.loads((folder / "chunks.json").read_text(encoding="utf-8"))
        store = cls.__new__(cls)
        store.index, store.metas = index, metas
        return store
