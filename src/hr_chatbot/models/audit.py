"""Immutable decision trail for compliance (plan §7 / §13).

Why this exists
---------------
Regulated workplaces need to reconstruct *why* the bot answered or escalated.
Each graph turn writes one AuditLog row with triage JSON, sources used, and
which Gemini model produced the reply — independent of LangGraph checkpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hr_chatbot.core.database import Base


class AuditLog(Base):
    """One auditable event for a conversation turn."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True
    )
    # e.g. ``triage``, ``retrieve``, ``respond``, ``escalate``
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    triage_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sources_used: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
