"""Employee identity model.

Why this exists
---------------
Conversations, escalations, and audit rows all hang off a stable user id.
``employee_id`` is the company HRIS identifier; ``role`` gates future admin
features (e.g. who may resolve escalations) without a separate auth service.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hr_chatbot.core.database import Base


class User(Base):
    """An employee who may chat with the policy assistant."""

    __tablename__ = "users"

    # UUIDs avoid sequential-id enumeration attacks on public-ish APIs.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # ``employee`` | ``hr_admin`` — coarse RBAC for escalation resolve endpoints.
    role: Mapped[str] = mapped_column(String(32), default="employee")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversations = relationship("Conversation", back_populates="user")
    escalations = relationship("Escalation", back_populates="user")
