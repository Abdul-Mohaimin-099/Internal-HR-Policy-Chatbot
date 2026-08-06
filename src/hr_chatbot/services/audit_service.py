"""Audit service — append-only decision trail writers.

Why this exists
---------------
Every graph turn should leave a reconstructable record (triage JSON, sources,
model id). Centralising inserts keeps event_type naming consistent across nodes.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.models.audit import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID | None,
    event_type: str,
    triage_result: dict[str, Any] | None = None,
    sources_used: list[Any] | dict[str, Any] | None = None,
    model_used: str | None = None,
) -> AuditLog:
    """Persist one audit event and return the row."""
    row = AuditLog(
        conversation_id=conversation_id,
        event_type=event_type,
        triage_result=triage_result,
        sources_used=sources_used,
        model_used=model_used,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
