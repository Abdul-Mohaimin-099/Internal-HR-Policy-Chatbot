"""Conversation and message models (ADR-001 / ADR-004).

Why this exists
---------------
LangGraph's Postgres checkpointer stores *graph state* blobs for multi-turn
memory. Separately, we store clean Human/AI text in ``messages`` so HR can
query history, cite sources, and audit without deserializing checkpoints.
``thread_id`` is the bridge between the two stores.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hr_chatbot.core.database import Base


class Conversation(Base):
    """One continuous employee ↔ chatbot exchange (a LangGraph thread)."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    # LangGraph checkpointer key — clients reuse this across turns for memory.
    thread_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    escalations = relationship("Escalation", back_populates="conversation")


class Message(Base):
    """A single turn (user question or assistant reply) with optional citations."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    # ``user`` | ``assistant`` | ``system``
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    # List of {filename, section, page, score} dicts when the reply was RAG-grounded.
    sources: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation = relationship("Conversation", back_populates="messages")
