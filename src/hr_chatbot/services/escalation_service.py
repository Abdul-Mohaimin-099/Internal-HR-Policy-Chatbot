"""Escalation service — create, review, and resolve human-in-the-loop tickets.

Why this exists
---------------
The escalate LangGraph path opens a Postgres ticket and returns a safe refusal.
HR then takes action outside the graph (HITL): inspect context, post a human
reply into the conversation, and/or mark the case resolved. Keeping rules here
avoids duplicating SQL across the escalate tool and admin HTTP endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hr_chatbot.models.conversation import Conversation, Message
from hr_chatbot.models.escalation import Escalation
from hr_chatbot.services import audit_service


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


async def get_escalation(
    session: AsyncSession, *, escalation_id: uuid.UUID
) -> Escalation | None:
    """Load one escalation with conversation messages + employee row for HITL review."""
    result = await session.execute(
        select(Escalation)
        .where(Escalation.id == escalation_id)
        .options(
            selectinload(Escalation.conversation).selectinload(Conversation.messages),
            selectinload(Escalation.user),
        )
    )
    return result.scalar_one_or_none()


async def _append_hr_message(
    session: AsyncSession,
    *,
    escalation: Escalation,
    hr_staff: str,
    message: str,
) -> Message:
    """Write an HR reply into the employee conversation and bump last_message_at."""
    content = message.strip()
    row = Message(
        conversation_id=escalation.conversation_id,
        role="hr",
        content=content,
        sources={
            "escalation_id": str(escalation.id),
            "responded_by": hr_staff,
            "human_in_the_loop": True,
        },
    )
    session.add(row)
    conversation = await session.get(Conversation, escalation.conversation_id)
    if conversation is not None:
        conversation.last_message_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def respond_to_escalation(
    session: AsyncSession,
    *,
    escalation_id: uuid.UUID,
    responded_by: str,
    message: str,
) -> Escalation | None:
    """HR HITL action: post a human reply while leaving the ticket open."""
    escalation = await get_escalation(session, escalation_id=escalation_id)
    if escalation is None:
        return None
    if escalation.status != "open":
        raise ValueError("Escalation is not open")

    await _append_hr_message(
        session,
        escalation=escalation,
        hr_staff=responded_by,
        message=message,
    )
    await audit_service.write_audit(
        session,
        conversation_id=escalation.conversation_id,
        event_type="hr_respond",
        triage_result={
            "escalation_id": str(escalation.id),
            "responded_by": responded_by,
            "category": escalation.category,
        },
        sources_used={"human_in_the_loop": True},
        model_used=f"hr:{responded_by}",
    )
    # Reload with messages for the API response.
    return await get_escalation(session, escalation_id=escalation_id)


async def resolve_escalation(
    session: AsyncSession,
    *,
    escalation_id: uuid.UUID,
    resolved_by: str,
    hr_message: str | None = None,
) -> Escalation | None:
    """Mark an escalation handled; optionally post a final HR reply first."""
    escalation = await get_escalation(session, escalation_id=escalation_id)
    if escalation is None:
        return None
    if escalation.status != "open":
        raise ValueError("Escalation is not open")

    if hr_message and hr_message.strip():
        await _append_hr_message(
            session,
            escalation=escalation,
            hr_staff=resolved_by,
            message=hr_message,
        )

    escalation.status = "resolved"
    escalation.resolved_by = resolved_by
    escalation.resolved_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(escalation)

    await audit_service.write_audit(
        session,
        conversation_id=escalation.conversation_id,
        event_type="hr_resolve",
        triage_result={
            "escalation_id": str(escalation.id),
            "resolved_by": resolved_by,
            "category": escalation.category,
            "had_hr_message": bool(hr_message and hr_message.strip()),
        },
        sources_used={"human_in_the_loop": True},
        model_used=f"hr:{resolved_by}",
    )
    return await get_escalation(session, escalation_id=escalation_id)
