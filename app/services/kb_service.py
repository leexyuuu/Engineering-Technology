# -*- coding: utf-8 -*-
"""知识库管理服务（阶段3批1）：上传 md/pdf → 自动切片 → 向量化入库 → 删除。

- 上传：校验类型/大小/重名 → 抽取文本 → 500 字切片入库 → 全量重建索引（立即生效）；
- 删除：软删除（status=deleted，保留审计痕迹；filename 加后缀让出唯一键）→ 重建索引；
- 种子：首次启动且库为空时，自动把 data/docs/ 下的制度文档入库。
原件保存到 data/uploads/ 供审计（对应"审计留痕"要求）。
"""
from __future__ import annotations

import io
from pathlib import Path

from sqlalchemy import func, select

from ..config import settings
from ..db import AsyncSessionLocal
from ..models import DocChunk, Document, User
from ..rag.chunker import chunk_markdown
from ..schemas import ApiError, ErrorCode
from .retrieval_service import retrieval

# 允许上传的文件类型
ALLOWED_EXTS = {".md", ".pdf"}


def extract_text(filename: str, data: bytes) -> str:
    """按扩展名抽取文本：md 直接解码，pdf 用 pypdf 逐页抽取。"""
    suffix = Path(filename).suffix.lower()
    if suffix == ".md":
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ApiError(ErrorCode.BAD_REQUEST, "Markdown 文件编码错误，请使用 UTF-8 编码") from exc
    # PDF：逐页抽取文本（扫描版 PDF 无文本层，会得到空结果）
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ApiError:
        raise
    except Exception as exc:   # noqa: BLE001
        raise ApiError(ErrorCode.BAD_REQUEST, f"PDF 解析失败：{exc}") from exc


class KBService:
    """知识库管理（管理员功能的服务实现，页面与 API 共用）。"""

    # ── 种子：首次启动自动入库 data/docs/ ──
    async def seed_if_empty(self) -> int:
        """库为空时把 data/docs/*.md 入库，返回入库文档数。"""
        async with AsyncSessionLocal() as db:
            count = (await db.execute(
                select(func.count()).select_from(Document)
                .where(Document.status == "active"))).scalar()
        if count:
            return 0
        n = 0
        for md in sorted(Path(settings.docs_dir).glob("*.md")):
            try:
                text = md.read_text(encoding="utf-8")
            except OSError:
                continue
            await self._create_document(md.name, text, uploader_id=None)
            n += 1
        return n

    # ── 内部：切片并写入 documents + doc_chunks ──
    async def _create_document(self, filename: str, text: str,
                               uploader_id: int | None) -> tuple[int, int]:
        """创建文档与切片记录，返回 (文档id, 切片数)。"""
        chunks = chunk_markdown(text, settings.chunk_size, source=filename)
        if not chunks:
            raise ApiError(ErrorCode.BAD_REQUEST, "文档内容为空，无法切片")
        async with AsyncSessionLocal() as db:
            doc = Document(
                filename=filename,
                title=Path(filename).stem,
                doc_type="综合",          # 阶段3批2 可在页面编辑分类/版本/生效日期
                version="v1",
                applicable_scope="全院",
                status="active",
                uploader_id=uploader_id,
                chunk_count=len(chunks),
            )
            db.add(doc)
            await db.flush()             # 拿到 doc.id 再写切片
            for c in chunks:
                db.add(DocChunk(document_id=doc.id, chunk_index=c["chunk_no"],
                                heading=c["heading"], content=c["content"]))
            await db.commit()
            return doc.id, len(chunks)

    # ── 上传（页面与 API 共用入口）──
    async def upload(self, filename: str | None, data: bytes,
                     uploader: User) -> dict:
        """上传文档：校验 → 抽取 → 切片入库 → 重建索引。"""
        if not filename or Path(filename).suffix.lower() not in ALLOWED_EXTS:
            raise ApiError(ErrorCode.BAD_REQUEST, "仅支持上传 Markdown(.md) 或 PDF(.pdf) 文件")
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise ApiError(ErrorCode.BAD_REQUEST,
                           f"文件过大（上限 {settings.max_upload_mb}MB）")
        if not data:
            raise ApiError(ErrorCode.BAD_REQUEST, "文件内容为空")

        # 重名校验（活跃文档中不允许同名，避免版本混淆）
        async with AsyncSessionLocal() as db:
            dup = (await db.execute(
                select(Document).where(Document.filename == filename,
                                       Document.status == "active"))).scalar_one_or_none()
        if dup:
            raise ApiError(ErrorCode.BAD_REQUEST, "同名文档已存在，请先删除旧版或改名后重传")

        text = extract_text(filename, data)
        if not text.strip():
            raise ApiError(ErrorCode.BAD_REQUEST, "未能从文件中提取到文本（扫描版 PDF 暂不支持）")

        # 原件留存（审计）
        Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
        (Path(settings.uploads_dir) / filename).write_bytes(data)

        doc_id, chunk_count = await self._create_document(filename, text, uploader.id)
        index_total = await retrieval.rebuild_from_db()   # 立即生效
        return {"id": doc_id, "filename": filename, "chunk_count": chunk_count,
                "index_total": index_total}

    # ── 列表 ──
    async def list_documents(self) -> list[dict]:
        """活跃文档列表（新上传在前）。"""
        async with AsyncSessionLocal() as db:
            docs = (await db.execute(
                select(Document).where(Document.status == "active")
                .order_by(Document.id.desc()))).scalars().all()
        return [{
            "id": d.id, "filename": d.filename, "title": d.title, "doc_type": d.doc_type,
            "version": d.version, "effective_date": d.effective_date,
            "applicable_scope": d.applicable_scope, "chunk_count": d.chunk_count,
            "uploader_id": d.uploader_id, "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        } for d in docs]

    # ── 删除（软删除 + 重建索引）──
    async def delete(self, doc_id: int) -> None:
        """软删除文档并重建索引（记录保留，文件名让出唯一键以便重新上传）。"""
        async with AsyncSessionLocal() as db:
            doc = await db.get(Document, doc_id)
            if doc is None or doc.status != "active":
                raise ApiError(ErrorCode.DOC_NOT_FOUND)
            doc.status = "deleted"
            doc.filename = f"{doc.filename}（已删除-{doc.id}）"   # 让出唯一键
            await db.commit()
        await retrieval.rebuild_from_db()   # 立即从索引移除


# 模块级单例
kb_service = KBService()
