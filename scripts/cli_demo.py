# -*- coding: utf-8 -*-
"""
阶段 1 · 裸问答原型（单文件命令行版，无 Web）
================================================================
排课选课与教务协作智能体系统 —— 第一周最小验证目标（MVP）

完整链路：
    本地教务制度 Markdown（seeds/教务管理制度.md）
      → 500 字切片                      【chunker】
      → 向量化并持久化到 FAISS           【embeddings + vector_store】
    命令行提问
      → BM25 + 向量混合检索 top3         【bm25 + retrieval，RRF 融合】
      → 拼装系统提示词 + 制度条文         【prompt_assembler】
      → 调用 LLM 流式生成回答            【llm_gateway，供应商可配置】
      → 终端输出：回答 + 引用来源 + 检索/首token/总耗时指标

运行示例：
    # 离线冒烟（默认 mock LLM + 本地哈希嵌入，无需任何 API Key）
    python scripts/cli_demo.py --rebuild --ask "补退选的截止时间是什么时候？"

    # 交互式问答
    python scripts/cli_demo.py

    # 接入真实 LLM：复制 .env.example 为 .env 并填写供应商信息后
    python scripts/cli_demo.py --rebuild

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【核心复用模块清单】标注 ★ 的代码块在阶段 2 平移进 app/ 包，不重写：
    ★ chunk_markdown()      → app/rag/chunker.py                 500 字切片
    ★ embed_texts()         → app/rag/embeddings.py              向量化（供应商可配置）
    ★ FAISSStore            → app/rag/vector_store.py            FAISS 检索/持久化
    ★ BM25Store             → app/rag/bm25.py                    BM25 词法索引
    ★ hybrid_retrieve()     → app/services/retrieval_service.py  混合检索（RRF）
    ★ sanitize_for_llm()    → app/agent/llm_gateway.py           出校脱敏（Q6）
    ★ stream_llm()          → app/agent/llm_gateway.py           LLM 调用（阶段2改异步+SSE）
    ★ build_messages()      → app/agent/prompt_assembler.py      提示词装配
    ★ DEFAULT_SYSTEM_PROMPT → 阶段 3 存入 prompt_templates 表（管理员后台可编辑）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List

import numpy as np
import faiss                      # 向量索引（IndexFlatIP = 内积，配合归一化即余弦相似度）
import jieba                      # 中文分词（BM25 与哈希嵌入共用）
from rank_bm25 import BM25Okapi   # BM25 词法检索实现

# 关闭 jieba 首次加载词典时的提示，保持终端输出干净
jieba.setLogLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# 路径常量：项目根目录 = scripts/ 的上一级；data/ 为运行时产物目录
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FAISS_DIR = DATA_DIR / "faiss"
DEFAULT_DOC = BASE_DIR / "seeds" / "教务管理制度.md"

# .env 加载（可选：没有 .env 时退化为读环境变量 / 使用内置默认值）
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════════════
# 配置（★ 阶段 2 平移至 app/config.py，用 pydantic-settings 强化校验）
# 所有供应商信息一律来自环境变量 / .env，代码中不出现密钥 —— 可替换供应商的基础
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class AppConfig:
    """运行配置：LLM / Embedding 供应商均可通过 .env 切换。"""
    llm_provider: str = "mock"            # mock=离线冒烟 / openai_compatible=真实调用
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: float = 60.0
    embedding_provider: str = "local_hash"   # local_hash=离线验证 / openai_compatible=真实
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    chunk_size: int = 500                 # 切片目标长度（字符）
    top_k: int = 3                        # 混合检索返回条数


def load_config() -> AppConfig:
    """从环境变量（含 .env）读取配置；缺省值保证离线也能跑通。"""
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_timeout=float(os.getenv("LLM_TIMEOUT", "60")),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local_hash").strip(),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "").strip(),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "").strip(),
        chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
        top_k=int(os.getenv("TOP_K", "3")),
    )


# ══════════════════════════════════════════════════════════════════════════
# 默认系统提示词（★ 阶段 3 平移：存入 prompt_templates 表，管理员后台可编辑，
# 修改后立即对问答生效 —— 不写死在代码里；此字符串仅作首次初始化的默认模板）
# ══════════════════════════════════════════════════════════════════════════
DEFAULT_SYSTEM_PROMPT = (
    "你是学校教务制度助手，只根据提供的制度条文回答，不确定时明确说'制度中未找到'，"
    "回答末尾附引用来源，不得编造排课或选课规则。"
)


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/agent/llm_gateway.py】出校脱敏（Q6 默认答案）
# 学生姓名/学号等隐私数据在发往外部 LLM 前替换为占位符，回填在本地完成。
# 阶段 1 为简版（正则识别学号/手机号/证件号）；阶段 2 扩展姓名词典 + 占位符回填。
# ══════════════════════════════════════════════════════════════════════════
def sanitize_for_llm(text: str) -> str:
    """把文本中的敏感编号替换为占位符，避免隐私数据出校。"""
    text = re.sub(r"\b\d{10,12}\b", "[学号已脱敏]", text)          # 10~12 位数字：学号
    text = re.sub(r"\b1[3-9]\d{9}\b", "[手机号已脱敏]", text)      # 11 位手机号
    text = re.sub(r"\b\d{17}[\dXx]\b", "[证件号已脱敏]", text)     # 18 位身份证
    return text


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/rag/chunker.py】500 字切片
# 策略：按行切段 → 遇到 Markdown 标题先落盘当前缓冲（保证切片不跨章节）
#      → 缓冲累计到 500 字即产出一片；超长单段按 500 字硬切。
# 切片元数据保留"所属章节标题"，用于引用来源展示（文件名+章节+片段号）。
# ══════════════════════════════════════════════════════════════════════════
def chunk_markdown(text: str, chunk_size: int = 500, source: str = "") -> List[Dict[str, Any]]:
    """把制度 Markdown 切成 <=chunk_size 的片段，返回切片元数据列表。"""
    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []          # 当前缓冲中的行
    heading = "（文档开头）"      # 当前活跃的章节标题

    def flush() -> None:
        """把缓冲落成一个切片。"""
        if not buf:
            return
        content = "\n".join(buf).strip()
        if content:
            chunks.append({
                "id": len(chunks),                       # 全局编号（FAISS 内部 id 与之对齐）
                "chunk_no": len(chunks),                 # 对外展示的片段号
                "source": source,                        # 来源文件名（引用展示用）
                "heading": heading,                      # 所属章节（引用展示用）
                "content": content,                      # 切片正文
                "embed_text": f"{heading}\n{content}",   # 参与向量化的文本（带标题增强检索）
            })
        buf.clear()

    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        if para.startswith("#"):
            # 标题行：先结束上一个章节的切片，再更新章节名 → 切片不跨章节
            flush()
            heading = re.sub(r"^#+\s*", "", para)
            continue
        if len(para) > chunk_size:
            # 超长单段（如整段贴入的表格文本）：按 chunk_size 硬切
            flush()
            for i in range(0, len(para), chunk_size):
                piece = para[i:i + chunk_size]
                chunks.append({
                    "id": len(chunks), "chunk_no": len(chunks), "source": source,
                    "heading": heading, "content": piece,
                    "embed_text": f"{heading}\n{piece}",
                })
            continue
        # 常规行：加入缓冲前判断是否会超长，超长则先落盘
        if sum(len(x) for x in buf) + len(para) >= chunk_size:
            flush()
        buf.append(para)
    flush()
    return chunks


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/rag/embeddings.py】向量化（供应商可配置）
# - openai_compatible：任意 OpenAI 兼容 /embeddings 端点（生产默认，分批 64 条）
# - local_hash：离线验证用的哈希词袋嵌入（无语义能力，仅保证整条管线可离线跑通；
#   此时检索质量主要依赖 BM25，真实环境必须切换到 API 嵌入）
# 两种供应商统一做 L2 归一化 → 与 FAISS IndexFlatIP 组合即为余弦相似度。
# ══════════════════════════════════════════════════════════════════════════
def embed_texts(texts: List[str], cfg: AppConfig) -> np.ndarray:
    """把一批文本转成 (n, dim) 的归一化 float32 向量矩阵。"""
    if cfg.embedding_provider == "openai_compatible":
        from openai import OpenAI   # 延迟导入：mock 模式无需安装后也可跑检索以外的逻辑
        client = OpenAI(base_url=cfg.embedding_base_url,
                        api_key=cfg.embedding_api_key, timeout=cfg.llm_timeout)
        vecs: List[List[float]] = []
        for i in range(0, len(texts), 64):   # 分批请求，避免单次超长
            resp = client.embeddings.create(model=cfg.embedding_model,
                                            input=texts[i:i + 64])
            vecs.extend(d.embedding for d in resp.data)
        mat = np.asarray(vecs, dtype="float32")
    else:
        # local_hash：把每个分词哈希到固定维度并计数 → 归一化词袋向量（离线冒烟用）
        dim = 256
        mat = np.zeros((len(texts), dim), dtype="float32")
        for row, t in enumerate(texts):
            for tok in jieba.lcut(t):
                idx = int.from_bytes(hashlib.md5(tok.encode("utf-8")).digest()[:4], "little") % dim
                mat[row, idx] += 1.0

    # L2 归一化：让内积（IP）等价于余弦相似度
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype("float32")


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/rag/vector_store.py】FAISS 封装
# 职责：建库（add）/ 检索（search）/ 持久化（save/load）。
# 阶段 3 的知识库管理页将复用 add + save 实现文档上传入库；
# delete 通过重建索引实现（IndexFlat 不支持删除，量小可接受）。
# ══════════════════════════════════════════════════════════════════════════
class FAISSStore:
    """FAISS 向量索引 + 切片元数据的统一封装。"""

    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)   # 内积索引（向量已归一化 → 余弦相似度）
        self.metas: List[Dict[str, Any]] = []  # 第 i 条向量对应的切片元数据

    def add(self, embeddings: np.ndarray, metas: List[Dict[str, Any]]) -> None:
        """批量写入向量与元数据（内部 id = 写入顺序 = 切片 id）。"""
        self.index.add(embeddings)
        self.metas.extend(metas)

    def search(self, qvec: np.ndarray, k: int = 10) -> List[tuple]:
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


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/rag/bm25.py】BM25 词法索引
# 中文分词用 jieba；检索只返回得分 > 0 的候选（零分不参与排名，
# 避免"全零分也硬排名"污染混合结果）。BM25 从 chunks.json 重建（代价低）。
# ══════════════════════════════════════════════════════════════════════════
class BM25Store:
    """BM25 词法检索（与 FAISSStore 共用切片元数据）。"""

    def __init__(self, metas: List[Dict[str, Any]]):
        self.metas = metas
        self._corpus = [list(jieba.lcut(m["embed_text"])) for m in metas]
        self.bm25 = BM25Okapi(self._corpus)

    def search(self, query: str, k: int = 10) -> List[tuple]:
        """返回 [(切片 id, BM25 得分)]，仅保留得分 > 0 的前 k 条。"""
        scores = self.bm25.get_scores(list(jieba.lcut(query)))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [(i, float(scores[i])) for i in order if scores[i] > 0][:k]


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/services/retrieval_service.py】
# BM25 + 向量 混合检索（RRF 倒数排名融合，k=60 为通用常数）：
#     rrf(切片) = Σ 1/(60 + 该切片在某路检索中的排名)
# 两路各取前 10 候选 → RRF 融合 → 输出 top_k。
# 词法（BM25）抓"条款号/专有名词"，向量抓"同义改写"，互补提升召回。
# 阶段 3 扩展点：版本过滤 + 冲突双版本返回（documents 表带 version 字段）。
# ══════════════════════════════════════════════════════════════════════════
def hybrid_retrieve(query: str, faiss_store: FAISSStore, bm25_store: BM25Store,
                    cfg: AppConfig, k: int | None = None) -> List[Dict[str, Any]]:
    """混合检索 top-k，返回按 RRF 降序的命中列表（含两路排名与得分，供解释展示）。"""
    k = k or cfg.top_k
    qvec = embed_texts([query], cfg)[0]                    # 查询向量化（同供应商）
    vec_hits = faiss_store.search(qvec, k=10)             # 向量路：前 10 候选
    bm_hits = bm25_store.search(query, k=10)              # 词法路：前 10 候选（零分已剔除）

    fused: Dict[int, Dict[str, Any]] = {}

    def entry(meta: Dict[str, Any]) -> Dict[str, Any]:
        """取或建该切片的融合条目。"""
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
        e = entry(bm25_store.metas[idx])
        e["rrf"] += 1.0 / (60 + rank)
        e["bm25_rank"], e["bm25_score"] = rank, round(score, 4)

    return sorted(fused.values(), key=lambda e: e["rrf"], reverse=True)[:k]


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/agent/prompt_assembler.py】提示词装配
# 组装规则：系统提示词（阶段 3 起从数据库读取）+ 编号制度条文 + 学生问题。
# 编号 [1][2][3] 与引用来源一一对应，保证回答可溯源（审计"事实引用"要素）。
# ══════════════════════════════════════════════════════════════════════════
def build_messages(question: str, hits: List[Dict[str, Any]],
                   system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> List[Dict[str, str]]:
    """把检索结果与学生问题装配成 LLM 消息列表（OpenAI 消息格式）。"""
    blocks = []
    for i, h in enumerate(hits, start=1):
        m = h["meta"]
        blocks.append(f"[{i}] 来源：{m['source']} · {m['heading']}（片段#{m['chunk_no']}）\n{m['content']}")
    context = "\n\n".join(blocks)
    user_msg = f"【制度条文检索结果】\n{context}\n\n【学生问题】\n{sanitize_for_llm(question)}"
    # 阶段 2 扩展点：在此插入"最近 6 轮对话历史"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]


# ══════════════════════════════════════════════════════════════════════════
# ★【核心复用模块 · 阶段 2 平移至 app/agent/llm_gateway.py】LLM 调用
# - 供应商可配置：mock（离线冒烟）/ openai_compatible（任意兼容端点）
# - 流式输出（yield 增量文本）：阶段 2 的 SSE 接口直接消费本生成器
# - 统一超时与中文错误信息：绝不静默失败（对应"异常兜底"上线要求）
# 阶段 2 改造点：同步 OpenAI → AsyncOpenAI；阶段 4 扩展 tools 参数（Function Calling）
# ══════════════════════════════════════════════════════════════════════════
def stream_llm(messages: List[Dict[str, str]], cfg: AppConfig) -> Iterator[str]:
    """调用 LLM 流式生成回答，逐段 yield 文本增量。"""
    if cfg.llm_provider == "mock":
        yield from _mock_llm(messages)          # 离线冒烟：不联网
        return

    if cfg.llm_provider != "openai_compatible" or not cfg.llm_api_key:
        # 配置不完整时给出明确中文错误（对应统一错误码规范的雏形）
        raise RuntimeError(f"[LLM 配置错误] 供应商={cfg.llm_provider}，"
                           f"请检查 .env 中的 LLM_PROVIDER / LLM_API_KEY 等配置")

    try:
        from openai import OpenAI
        client = OpenAI(base_url=cfg.llm_base_url or None,
                        api_key=cfg.llm_api_key, timeout=cfg.llm_timeout,
                        max_retries=1)   # 只重试 1 次，避免长阻塞
        resp = client.chat.completions.create(
            model=cfg.llm_model, messages=messages,
            stream=True, temperature=0.1,   # 低温度：制度问答要求稳定、不发散
        )
        for delta in resp:
            piece = delta.choices[0].delta.content if delta.choices else None
            if piece:
                yield piece
    except Exception as exc:   # noqa: BLE001 —— 网络库异常类型多，统一转中文提示
        raise RuntimeError(f"[LLM 调用失败] 供应商={cfg.llm_provider} 模型={cfg.llm_model}，"
                           f"错误详情：{exc}") from exc


def _mock_llm(messages: List[Dict[str, str]]) -> Iterator[str]:
    """
    mock 供应商（仅阶段 1 离线冒烟用）：
    不联网，用"词面重叠抽取"模拟回答 —— 验证 检索→提示词→流式输出 整条管线。
    · 与问题无任何词面重叠 → 回答"制度中未找到"（模拟陷阱题的正确行为）
    · 有重叠 → 从最佳片段抽取相关句子并附引用
    生产环境必须使用真实供应商；"未找到"的判断在生产中由 LLM 依据系统提示词完成。
    """
    user_msg = messages[-1]["content"]

    m = re.search(r"【学生问题】\s*(.+)$", user_msg, re.S)
    question = m.group(1).strip() if m else ""
    q_tokens = {t for t in jieba.lcut(question) if len(t) > 1}

    blocks = re.findall(r"\[(\d+)\] 来源：([^\n]+)\n(.*?)(?=\n\n\[|\n\n【|$)",
                        user_msg, re.S)

    scored = []
    for no, src, body in blocks:
        b_tokens = {t for t in jieba.lcut(body) if len(t) > 1}
        overlap = len(q_tokens & b_tokens)
        if overlap > 0:
            scored.append((overlap, no, src, body))

    if not scored:   # 陷阱题：检索上下文与问题零重叠
        yield "（mock 供应商·离线演示）制度中未找到与该问题相关的条文。建议换一种问法，或咨询教务管理员。"
        return

    scored.sort(reverse=True)
    _, no, src, body = scored[0]
    # 抽取句子作为"回答"：按与问题的词面重叠数降序取前 3 句（确定性输出，便于冒烟比对）
    scored_sent = []
    for sent in re.split(r"[。；;]", body):
        s_tokens = {t for t in jieba.lcut(sent) if len(t) > 1}
        cleaned = sent.strip(" ：:，,\n\t ")   # 去掉跨行句子首尾的空白，避免空行符号
        overlap = len(s_tokens & q_tokens)
        if overlap > 0 and len(cleaned) > 4:
            scored_sent.append((overlap, cleaned))
    scored_sent.sort(reverse=True)
    yield f"（mock 供应商·离线演示）根据制度条文[{no}]：\n"
    for _, s in scored_sent[:3]:
        yield f"· {s}。\n"
    yield f"\n引用来源：[{no}] {src}\n"


# ══════════════════════════════════════════════════════════════════════════
# 问答主流程（阶段 2 平移至 app/services/chat_service.py，
# 打字机/状态展示逻辑届时由前端实现，此处终端版承担同样的演示职责）
# ══════════════════════════════════════════════════════════════════════════
def answer_once(question: str, faiss_store: FAISSStore, bm25_store: BM25Store,
                cfg: AppConfig) -> None:
    """完成一次"检索 → 装配 → LLM 流式回答 → 引用与指标展示"。"""
    print("─" * 64)
    print("🔍 正在检索教务制度…")          # 对应阶段 2 前端的"正在检索教务制度…"状态

    t0 = time.perf_counter()
    hits = hybrid_retrieve(question, faiss_store, bm25_store, cfg)
    t_retrieve = (time.perf_counter() - t0) * 1000

    print(f"📄 混合检索命中 {len(hits)} 段（BM25+向量 RRF 融合，top{cfg.top_k}）：")
    for i, h in enumerate(hits, start=1):
        m = h["meta"]
        rank_info = f"BM25排名#{h['bm25_rank'] or '-'} 向量排名#{h['vec_rank'] or '-'}"
        print(f"  [{i}] {m['source']} · {m['heading']}（片段#{m['chunk_no']}）"
              f"  RRF={h['rrf']:.4f}  {rank_info}")
        print(f"      预览：{m['content'][:40]}…")

    messages = build_messages(question, hits)

    print("💬 回答：")
    t1 = time.perf_counter()
    first_token_ms = None
    full: List[str] = []
    try:
        for piece in stream_llm(messages, cfg):
            if first_token_ms is None:
                first_token_ms = (time.perf_counter() - t1) * 1000
            full.append(piece)
            sys.stdout.write(piece)      # 逐段写出 → 终端"打字机"效果
            sys.stdout.flush()
    except RuntimeError as exc:
        print(f"\n❌ 回答生成失败：{exc}")
        print("   兜底建议：请检查供应商配置，或稍后重试；紧急问题请联系教务管理员。")
        return
    print()

    # 引用来源展示（阶段 2 前端在回答底部渲染同样的数据）
    print("📚 引用来源：")
    for i, h in enumerate(hits, start=1):
        m = h["meta"]
        print(f"  [{i}] {m['source']} · {m['heading']}（片段#{m['chunk_no']}）")

    total_ms = (time.perf_counter() - t0) * 1000
    ft = f"{first_token_ms:.0f}ms" if first_token_ms is not None else "-"
    print(f"⏱ 指标：检索 {t_retrieve:.0f}ms · 首token {ft} · 总耗时 {total_ms:.0f}ms")


def build_or_load_index(cfg: AppConfig, doc_path: Path, rebuild: bool):
    """建库或加载持久化索引；返回 (FAISSStore, BM25Store, 切片数)。"""
    persisted = FAISS_DIR / "index.faiss"
    if not rebuild and persisted.exists():
        faiss_store = FAISSStore.load(FAISS_DIR)
        bm25_store = BM25Store(faiss_store.metas)     # BM25 由元数据快速重建
        print(f"[索引] 已加载持久化索引：{faiss_store.index.ntotal} 段（如需重建请加 --rebuild）")
        return faiss_store, bm25_store, faiss_store.index.ntotal

    text = doc_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text, cfg.chunk_size, source=doc_path.name)
    embeddings = embed_texts([c["embed_text"] for c in chunks], cfg)
    faiss_store = FAISSStore(dim=embeddings.shape[1])
    faiss_store.add(embeddings, chunks)
    faiss_store.save(FAISS_DIR)
    bm25_store = BM25Store(chunks)
    print(f"[建库] 《{doc_path.name}》 切片 {len(chunks)} 段 · "
          f"向量维度 {embeddings.shape[1]} · 已存入 {FAISS_DIR.relative_to(BASE_DIR)}")
    return faiss_store, bm25_store, len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="阶段1 · 教务制度裸问答原型")
    parser.add_argument("--ask", help="单次问答模式：直接传入问题（便于自动化测试）")
    parser.add_argument("--rebuild", action="store_true", help="强制重建索引（文档更新后使用）")
    parser.add_argument("--doc", default=str(DEFAULT_DOC), help="制度文档路径（默认 seeds/教务管理制度.md）")
    args = parser.parse_args()

    cfg = load_config()
    doc_path = Path(args.doc)
    if not doc_path.exists():
        print(f"❌ [文件不存在] {doc_path}")
        sys.exit(1)

    print("════════════ 阶段 1 · 裸问答原型 ════════════")
    print(f"LLM 供应商: {cfg.llm_provider} | Embedding: {cfg.embedding_provider} "
          f"| 切片: {cfg.chunk_size}字 | TopK: {cfg.top_k}")

    faiss_store, bm25_store, _ = build_or_load_index(cfg, doc_path, args.rebuild)

    if args.ask:                       # 单次问答模式
        answer_once(args.ask, faiss_store, bm25_store, cfg)
        return

    # 交互式 REPL 模式
    print("输入问题进行提问；输入 exit / 退出 结束。")
    while True:
        try:
            question = input("\n👤 学生 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit", "q", "退出"}:
            break
        answer_once(question, faiss_store, bm25_store, cfg)
    print("再见！")


if __name__ == "__main__":
    main()
