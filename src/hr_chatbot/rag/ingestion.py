"""Document ingestion: Docling parse → chunk → embed → Qdrant + Postgres.

Why this exists
---------------
HR admins upload PDF/Markdown policy files. We must turn them into searchable
vectors without losing source metadata (filename, section, page) so answers can
cite the exact policy excerpt that grounded them (plan §5.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.models.document import DocumentChunk, PolicyDocument
from hr_chatbot.rag.embeddings import embed_documents
from hr_chatbot.rag.retriever import delete_points, upsert_chunks

logger = get_logger(__name__)


@dataclass
class ParsedChunk:
    """Intermediate chunk before embedding / persistence."""

    text: str
    section: str | None
    page_number: int | None
    chunk_index: int


def _parse_with_docling(path: Path) -> str:
    """Extract plain text from PDF/Markdown via Docling only.

    On Windows, Docling's layout model can trigger PyTorch Inductor, which
    needs MSVC ``cl.exe``. We disable torch.compile so Docling runs without
    Build Tools. For full Inductor acceleration, install Visual Studio Build
    Tools (Desktop development with C++) and remove the TORCHDYNAMO_DISABLE
    overrides below.
    """
    import os

    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".markdown"}:
        return path.read_text(encoding="utf-8")

    # Force-disable torch.compile so Docling does not need ``cl.exe`` on Windows.
    os.environ["TORCHDYNAMO_DISABLE"] = "1"
    os.environ["TORCH_COMPILE_DISABLE"] = "1"
    os.environ["TORCHINDUCTOR_DISABLE"] = "1"

    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(path))
    markdown = result.document.export_to_markdown()
    if not markdown or not markdown.strip():
        raise ValueError(f"Docling returned empty text for {path.name}")
    return markdown


def _guess_section(text: str) -> str | None:
    """Pull the first markdown heading from a chunk as a soft section label."""
    match = re.search(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def chunk_text(text: str) -> list[ParsedChunk]:
    """Split policy text into overlapping windows.

    RecursiveCharacterTextSplitter prefers paragraph/sentence boundaries over
    hard char cuts, which keeps citations readable. Overlap preserves context
    that would otherwise be severed at chunk borders.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    pieces = splitter.split_text(text)
    return [
        ParsedChunk(
            text=piece,
            section=_guess_section(piece),
            page_number=None,  # Docling page map is optional; leave null when unknown
            chunk_index=i,
        )
        for i, piece in enumerate(pieces)
        if piece.strip()
    ]


async def ingest_file(
    session: AsyncSession,
    *,
    path: Path,
    title: str | None = None,
    version: str = "1.0",
    document_id: UUID | None = None,
) -> PolicyDocument:
    """Full ingest pipeline for one file; returns the persisted PolicyDocument.

    Steps: parse → chunk → embed (gemini-embedding-2) → upsert Qdrant →
    write ``policy_documents`` + ``document_chunks`` rows. If ``document_id``
    is set we treat this as a reindex: old Qdrant points are deleted first.
    """
    path = path.resolve()
    logger.info("Ingesting policy file=%s", path)

    # --- Reindex path: wipe prior vectors + chunk rows ---
    if document_id is not None:
        existing = await session.get(PolicyDocument, document_id)
        if existing is None:
            raise ValueError(f"PolicyDocument {document_id} not found")
        old_ids = [
            row.qdrant_point_id
            for row in (
                await session.execute(
                    select(DocumentChunk).where(DocumentChunk.document_id == document_id)
                )
            ).scalars()
        ]
        delete_points(old_ids)
        for row in (
            await session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
        ).scalars():
            await session.delete(row)
        doc = existing
        doc.filename = path.name
        doc.title = title or path.stem.replace("_", " ")
        doc.version = version
        doc.storage_path = str(path)
    else:
        doc = PolicyDocument(
            filename=path.name,
            title=title or path.stem.replace("_", " "),
            version=version,
            storage_path=str(path),
        )
        session.add(doc)
        await session.flush()  # assign doc.id before building payloads

    raw = _parse_with_docling(path)
    parsed = chunk_text(raw)
    if not parsed:
        raise ValueError(f"No text chunks extracted from {path.name}")

    vectors = embed_documents([c.text for c in parsed])
    point_ids = [str(uuid4()) for _ in parsed]
    payloads = [
        {
            "text": c.text,
            "document_id": str(doc.id),
            "filename": doc.filename,
            "section": c.section,
            "page_number": c.page_number,
            "chunk_index": c.chunk_index,
        }
        for c in parsed
    ]
    upsert_chunks(vectors=vectors, payloads=payloads, point_ids=point_ids)

    for c, pid in zip(parsed, point_ids, strict=True):
        session.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_text=c.text,
                chunk_index=c.chunk_index,
                section=c.section,
                page_number=c.page_number,
                qdrant_point_id=pid,
            )
        )

    doc.chunk_count = len(parsed)
    await session.commit()
    await session.refresh(doc)
    logger.info("Ingested %s chunks=%s", doc.filename, doc.chunk_count)
    return doc
