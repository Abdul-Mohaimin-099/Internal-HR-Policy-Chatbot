"""Escalation service — create and resolve human-review tickets.

Why this exists
---------------
The escalate LangGraph node and the HR admin HTTP endpoints share the same
business rules (status transitions, timestamps). Keeping them in a service
avoids duplicating SQL across layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.models.escalation import Escalation


async def create_escalation(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    category: str,
    reason: str,
) -> Escalation:
    """Open a new ``open`` escalation for HR to pick up."""
    row = Escalation(
        conversation_id=conversation_id,
        user_id=user_id,
        category=category,
        reason=reason,
        status="open",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_escalations(
    session: AsyncSession, *, status: str | None = "open"
) -> list[Escalation]:
    """List escalations, defaulting to open cases for the HR queue."""
    stmt = select(Escalation).order_by(Escalation.created_at.desc())
    if status:
        stmt = stmt.where(Escalation.status == status)
    return list((await session.execute(stmt)).scalars().all())


async def resolve_escalation(
    session: AsyncSession,
    *,
    escalation_id: uuid.UUID,
    resolved_by: str,
) -> Escalation | None:
    """Mark an escalation handled; returns None if the id is unknown."""
    row = await session.get(Escalation, escalation_id)
    if row is None:
        return None
    row.status = "resolved"
    row.resolved_by = resolved_by
    row.resolved_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row
