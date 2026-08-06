"""Document upload / list / reindex endpoints (plan §6 Phase 2).

Why this exists
---------------
HR admins push policy PDFs into the system here. Upload runs the full ingest
pipeline (Docling → chunk → gemini-embedding-2 → Qdrant + Postgres). Reindex
rebuilds vectors after a policy file changes on disk.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.api.v1.schemas import (
    DocumentOut,
    DocumentUploadResponse,
    ReindexRequest,
)
from hr_chatbot.core.config import settings
from hr_chatbot.core.database import get_db
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.models.document import PolicyDocument
from hr_chatbot.rag.ingestion import ingest_file

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

# Uploaded originals land here so reindex can re-read them later.
_UPLOAD_DIR = Path("data/uploads")
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    version: str = Form(default="1.0"),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Accept a PDF/Markdown upload, persist it, and index into Qdrant."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".md", ".markdown", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Markdown/text uploads are supported",
        )

    dest = _UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        doc = await ingest_file(
            session, path=dest, title=title, version=version
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ingestion failed: {exc}",
        ) from exc

    return DocumentUploadResponse(document=DocumentOut.model_validate(doc))


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    session: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    """List all indexed policy documents and their chunk counts."""
    rows = (
        await session.execute(
            select(PolicyDocument).order_by(PolicyDocument.uploaded_at.desc())
        )
    ).scalars().all()
    return [DocumentOut.model_validate(r) for r in rows]


@router.post("/reindex", response_model=list[DocumentOut])
async def reindex_documents(
    body: ReindexRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    """Rebuild Qdrant vectors for one document or every known storage_path."""
    body = body or ReindexRequest()
    if body.document_id:
        docs = [await session.get(PolicyDocument, body.document_id)]
        if docs[0] is None:
            raise HTTPException(status_code=404, detail="Document not found")
    else:
        docs = list(
            (
                await session.execute(select(PolicyDocument))
            ).scalars().all()
        )

    updated: list[DocumentOut] = []
    for doc in docs:
        path = Path(doc.storage_path)
        if not path.exists():
            logger.warning("Skipping missing file %s", path)
            continue
        refreshed = await ingest_file(
            session,
            path=path,
            title=doc.title,
            version=doc.version,
            document_id=doc.id,
        )
        updated.append(DocumentOut.model_validate(refreshed))

    # Touch settings so unused-import linters stay quiet if collection name is logged.
    logger.info("Reindex complete collection=%s", settings.QDRANT_COLLECTION)
    return updated
