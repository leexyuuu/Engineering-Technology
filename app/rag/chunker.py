# -*- coding: utf-8 -*-
"""500 字切片（阶段2，由阶段1原型平移）。

策略：按行切段 → 遇 Markdown 标题先落盘当前缓冲（保证切片不跨章节）
→ 缓冲累计到 chunk_size 即产出一片；超长单段按 chunk_size 硬切。
切片元数据保留"所属章节标题"，用于引用来源展示（文件名 + 章节 + 片段号）。
阶段3 扩展点：上传 pdf 时先抽文本再走同一入口。
"""
from __future__ import annotations

import re
from typing import Any


def chunk_markdown(text: str, chunk_size: int = 500, source: str = "") -> list[dict[str, Any]]:
    """把制度 Markdown 切成 <=chunk_size 的片段，返回切片元数据列表。"""
    chunks: list[dict[str, Any]] = []
    buf: list[str] = []            # 当前缓冲中的行
    heading = "（文档开头）"        # 当前活跃的章节标题

    def flush() -> None:
        """把缓冲落成一个切片。"""
        if not buf:
            return
        content = "\n".join(buf).strip()
        if content:
            chunks.append({
                "id": len(chunks),                       # 全局编号（FAISS 内部 id 对齐）
                "chunk_no": len(chunks),                 # 对外展示的片段号
                "source": source,                        # 来源文件名（引用展示）
                "heading": heading,                      # 所属章节（引用展示）
                "content": content,                      # 切片正文
                "embed_text": f"{heading}\n{content}",   # 向量化文本（带标题增强检索）
            })
        buf.clear()

    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        if para.startswith("#"):
            # 标题行：先结束上一章节的切片，再更新章节名 → 切片不跨章节
            flush()
            heading = re.sub(r"^#+\s*", "", para)
            continue
        if len(para) > chunk_size:
            # 超长单段（如整段贴入的表格文本）：按 chunk_size 硬切
            flush()
            for i in range(0, len(para), chunk_size):
                piece = para[i:i + chunk_size]
                chunks.append({"id": len(chunks), "chunk_no": len(chunks), "source": source,
                               "heading": heading, "content": piece,
                               "embed_text": f"{heading}\n{piece}"})
            continue
        # 常规行：加入缓冲前判断是否超长，超长则先落盘
        if sum(len(x) for x in buf) + len(para) >= chunk_size:
            flush()
        buf.append(para)
    flush()
    return chunks
