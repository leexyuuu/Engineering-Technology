# -*- coding: utf-8 -*-
"""制度规则检索工具（阶段4，提示词7）：search_selection_rules。

- 直接复用阶段 1-3 的混合检索服务（BM25 + 向量 RRF 融合），
  知识库热更新（管理员上传/删除文档）对本工具即时生效；
- 返回带编号的条文片段，供模型在回答中标注引用来源（审计"事实引用"要素）；
- 检索失败时返回结构化错误（由 Agent 循环决定兜底话术），不抛异常中断对话。
"""
from __future__ import annotations

from typing import Any

from ...services.retrieval_service import retrieval


async def search_selection_rules(ctx, arguments: dict[str, Any]) -> dict[str, Any]:
    """工具3：按自然语言查询选课/排课制度条文（RAG 检索 top_k 条）。"""
    query = str(arguments.get("query", "")).strip()
    if not query:
        return {"found": False, "message": "查询关键词为空，请补充要查的制度问题。"}

    try:
        hits = await retrieval.retrieve(query)
    except Exception as exc:   # noqa: BLE001 —— 检索故障不中断对话，交由模型兜底
        return {"found": False, "error": True,
                "message": f"制度检索服务暂时不可用（{exc}），请稍后再试。"}

    if not hits:
        return {"found": False,
                "message": "制度中未找到与该问题相关的条文，建议咨询教务管理员。"}

    rules = []
    for i, h in enumerate(hits, start=1):
        meta = h["meta"]
        rules.append({
            "index": i,
            "source": meta["source"],          # 来源文件（含版本，审计"资料版本"）
            "heading": meta["heading"],        # 所属章节
            "chunk_no": meta["chunk_no"],      # 片段号（可回查原文）
            "content": meta["content"][:200],  # 摘要截断，避免提示词过长
        })
    return {"found": True, "query": query, "rules": rules}
