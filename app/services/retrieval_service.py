# -*- coding: utf-8 -*-
"""混合检索服务（阶段3：知识库改为数据库驱动）。

- 数据源：documents(active) + doc_chunks 两表（阶段2 扫描目录的方式废弃）；
- rebuild_from_db()：全量重建 FAISS + BM25 —— 上传/删除文档后调用，立即生效；
- load_or_build()：启动时加载持久化索引；索引缺失或数据库有更新则重建；
- 检索：BM25 + 向量各取前 10 候选 → RRF 倒数排名融合 → top_k。
  词法（BM25）抓"条款号/专有名词"，向量抓"同义改写"，互补提升召回。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..config import settings
from ..db import AsyncSessionLocal
from ..models import DocChunk, Document
from ..rag.bm25 import BM25Store
from ..rag.embeddings import embed_texts
from ..rag.vector_store import FAISSStore


class RetrievalService:
    """知识库检索单例（数据库为唯一事实来源，FAISS 文件是可重建缓存）。"""

    def __init__(self) -> None:
        self.faiss_store: FAISSStore | None = None
        self.bm25_store: BM25Store | None = None

    # ── 全量重建：从数据库读全部活跃切片 → 向量化 → FAISS + BM25 ──
    async def rebuild_from_db(self) -> int:
        """重建索引，返回切片总数（上传/删除文档后调用，立即生效）。"""
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(DocChunk, Document)
                .join(Document, DocChunk.document_id == Document.id)
                .where(Document.status == "active")
                .order_by(Document.id, DocChunk.chunk_index)
            )).all()

        metas: list[dict[str, Any]] = []
        for i, (chunk, doc) in enumerate(rows):
            metas.append({
                "id": i,                        # 全局编号（FAISS 内部 id 对齐）
                "chunk_no": chunk.chunk_index,  # 文档内片段号（引用展示）
                "source": doc.filename,         # 来源文件名（引用展示）
                "heading": chunk.heading,       # 所属章节（引用展示）
                "content": chunk.content,
                "embed_text": f"{chunk.heading}\n{chunk.content}",
            })

        embeddings = await embed_texts([m["embed_text"] for m in metas])
        self.faiss_store = FAISSStore(dim=embeddings.shape[1])
        self.faiss_store.add(embeddings, metas)
        self.faiss_store.save(settings.faiss_dir)              # 持久化（下次启动可直载）
        self.bm25_store = BM25Store(metas)
        return len(metas)

    async def _index_stale(self) -> bool:
        """索引缺失，或数据库文档有更新（晚于索引文件）→ 需要重建。"""
        idx = Path(settings.faiss_dir) / "index.faiss"
        if not idx.exists():
            return True
        async with AsyncSessionLocal() as db:
            total = (await db.execute(select(func.count()).select_from(Document))).scalar()
            latest = (await db.execute(select(func.max(Document.updated_at)))).scalar()
        if not total:
            return True
        if latest is None:
            return False
        return latest.timestamp() > idx.stat().st_mtime

    async def load_or_build(self) -> int:
        """启动时装载：优先加载持久化索引；过期/缺失则从数据库重建。"""
        if self.faiss_store is not None:
            return len(self.faiss_store.metas)
        if await self._index_stale():
            return await self.rebuild_from_db()
        self.faiss_store = FAISSStore.load(settings.faiss_dir)
        self.bm25_store = BM25Store(self.faiss_store.metas)
        return len(self.faiss_store.metas)

    # ── 混合检索：RRF 融合 top_k ──
    async def retrieve(self, query: str) -> list[dict[str, Any]]:
        """返回按 RRF 降序的命中列表（含两路排名与得分，供引用展示）。"""
        if self.faiss_store is None or self.bm25_store is None:
            raise RuntimeError("知识库未初始化")

        qvec = (await embed_texts([query]))[0]
        vec_hits = self.faiss_store.search(qvec, k=10)    # 向量路：前 10 候选
        bm_hits = self.bm25_store.search(query, k=10)     # 词法路：前 10 候选（零分已剔除）

        fused: dict[int, dict[str, Any]] = {}

        def entry(meta: dict[str, Any]) -> dict[str, Any]:
            if meta["id"] not in fused:
                fused[meta["id"]] = {
                    "meta": meta, "rrf": 0.0,
                    "bm25_rank": None, "bm25_score": 0.0,
                    "vec_rank": None, "vec_score": 0.0,
                }
            return fused[meta["id"]]

        for rank, (meta, score) in enumerate(vec_hits, start=1):
            e = entry(meta)
            e["rrf"] += 1.0 / (60 + rank)
            e["vec_rank"], e["vec_score"] = rank, round(score, 4)

        for rank, (idx, score) in enumerate(bm_hits, start=1):
            e = entry(self.bm25_store.metas[idx])
            e["rrf"] += 1.0 / (60 + rank)
            e["bm25_rank"], e["bm25_score"] = rank, round(score, 4)

        return sorted(fused.values(), key=lambda e: e["rrf"], reverse=True)[:settings.top_k]


# 模块级单例：入口层与服务层共用同一份索引
retrieval = RetrievalService()
