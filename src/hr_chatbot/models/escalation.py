"""Human-review escalation cases for high-sensitivity queries.

Why this exists
---------------
Harassment, termination, and medical topics must never get automated advice
(plan §4 / §13). Instead we create an Escalation row, return a safe
acknowledgment to the employee, and let HR take human-in-the-loop action
(inspect context, reply, resolve) via the escalations API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hr_chatbot.core.database import Base


class Escalation(Base):
    """A ticket opened when triage decides a human must handle the question."""

    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    # Closed policy category from triage (e.g. ``conduct``, ``medical``).
    category: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    # ``open`` | ``resolved``
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    conversation = relationship("Conversation", back_populates="escalations")
    user = relationship("User", back_populates="escalations")
