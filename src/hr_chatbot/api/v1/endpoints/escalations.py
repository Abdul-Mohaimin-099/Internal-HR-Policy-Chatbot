"""Escalation queue + human-in-the-loop actions for HR staff (plan §6 Phase 4).

After chat creates an open ticket, HR can:
1. List / inspect the case with conversation context
2. Post a human reply (``respond``) while keeping the ticket open
3. Resolve the case (optionally with a final ``hr_message``)

This is ticket-queue HITL — the LangGraph chat turn already finished with a
safe refusal; HR action happens via these endpoints, not graph interrupt.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.api.v1.schemas import (
    EscalationDetailOut,
    EscalationOut,
    HrRespondRequest,
    MessageOut,
    ResolveEscalationRequest,
)
from hr_chatbot.core.database import get_db
from hr_chatbot.models.escalation import Escalation
from hr_chatbot.services import escalation_service

router = APIRouter(prefix="/escalations", tags=["Escalations"])


def _to_detail(row: Escalation) -> EscalationDetailOut:
    conversation = row.conversation
    messages = []
    thread_id = ""
    if conversation is not None:
        thread_id = conversation.thread_id
        # Stable chronological order for HR review.
        ordered = sorted(conversation.messages or [], key=lambda m: m.created_at)
        messages = [MessageOut.model_validate(m) for m in ordered]
    employee_id = None
    if row.user is not None:
        employee_id = row.user.employee_id
    base = EscalationOut.model_validate(row)
    return EscalationDetailOut(
        **base.model_dump(),
        thread_id=thread_id,
        employee_id=employee_id,
        messages=messages,
    )


@router.get("", response_model=list[EscalationOut])
async def list_open_escalations(
    status_filter: str | None = Query(default="open", alias="status"),
    session: AsyncSession = Depends(get_db),
) -> list[EscalationOut]:
    """List escalation tickets (default: open cases awaiting HR)."""
    rows = await escalation_service.list_escalations(session, status=status_filter)
    return [EscalationOut.model_validate(r) for r in rows]


@router.get("/{escalation_id}", response_model=EscalationDetailOut)
async def get_escalation(
    escalation_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> EscalationDetailOut:
    """Return one ticket with conversation messages for HR review."""
    row = await escalation_service.get_escalation(session, escalation_id=escalation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _to_detail(row)


@router.post("/{escalation_id}/respond", response_model=EscalationDetailOut)
async def respond_to_escalation(
    escalation_id: UUID,
    body: HrRespondRequest,
    session: AsyncSession = Depends(get_db),
) -> EscalationDetailOut:
    """Human-in-the-loop: post an HR reply; ticket remains ``open``."""
    try:
        row = await escalation_service.respond_to_escalation(
            session,
            escalation_id=escalation_id,
            responded_by=body.responded_by,
            message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _to_detail(row)


@router.post("/{escalation_id}/resolve", response_model=EscalationDetailOut)
async def resolve_escalation(
    escalation_id: UUID,
    body: ResolveEscalationRequest,
    session: AsyncSession = Depends(get_db),
) -> EscalationDetailOut:
    """Resolve a ticket; optionally write a final HR message into the conversation."""
    try:
        row = await escalation_service.resolve_escalation(
            session,
            escalation_id=escalation_id,
            resolved_by=body.resolved_by,
            hr_message=body.hr_message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _to_detail(row)
