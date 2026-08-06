"""Policy document + chunk mapping models (ADR-003 bridge to Qdrant).

Why this exists
---------------
Qdrant holds dense vectors; Postgres holds human-readable document metadata
and a ``qdrant_point_id`` so we can delete/reindex vectors when a PDF is
updated without orphaning points in the cloud collection.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hr_chatbot.core.database import Base


class PolicyDocument(Base):
    """Metadata for an uploaded HR policy file that has been (or will be) indexed."""

    __tablename__ = "policy_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    filename: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(512))
    version: Mapped[str] = mapped_column(String(64), default="1.0")
    # Absolute or relative path on disk for reindex jobs.
    storage_path: Mapped[str] = mapped_column(String(1024))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """One text segment of a policy doc, linked to its Qdrant vector point."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_documents.id"), index=True
    )
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    # Optional structural hints from Docling (heading path / page).
    section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # UUID string of the point in Qdrant — used for delete / upsert targeting.
    qdrant_point_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    document = relationship("PolicyDocument", back_populates="chunks")
