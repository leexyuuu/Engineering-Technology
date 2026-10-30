# -*- coding: utf-8 -*-
"""BM25 词法索引（阶段1 起核心复用模块）。

中文分词用 jieba；检索只返回得分 > 0 的候选（零分不参与排名，
避免"全零分也硬排名"污染混合检索结果）。BM25 由切片元数据重建（代价低）。
空知识库时 bm25=None，search 返回空列表（rank_bm25 不支持空语料）。
"""
from __future__ import annotations

from typing import Any

import jieba
from rank_bm25 import BM25Okapi


class BM25Store:
    """BM25 词法检索（与 FAISSStore 共用切片元数据）。"""

    def __init__(self, metas: list[dict[str, Any]]):
        self.metas = metas
        self._corpus = [list(jieba.lcut(m["embed_text"])) for m in metas]
        self.bm25 = BM25Okapi(self._corpus) if self._corpus else None

    def search(self, query: str, k: int = 10) -> list[tuple]:
        """返回 [(切片 id, BM25 得分)]，仅保留得分 > 0 的前 k 条。"""
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(list(jieba.lcut(query)))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [(i, float(scores[i])) for i in order if scores[i] > 0][:k]
