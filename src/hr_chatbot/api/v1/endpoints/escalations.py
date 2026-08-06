"""Escalation queue endpoints for HR staff (plan §6 Phase 4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from hr_chatbot.api.v1.schemas import EscalationOut, ResolveEscalationRequest
from hr_chatbot.core.database import get_db
from hr_chatbot.services import escalation_service

router = APIRouter(prefix="/escalations", tags=["Escalations"])


@router.get("", response_model=list[EscalationOut])
async def list_open_escalations(
    status_filter: str | None = Query(default="open", alias="status"),
    session: AsyncSession = Depends(get_db),
) -> list[EscalationOut]:
    """List escalation tickets (default: open cases awaiting HR)."""
    rows = await escalation_service.list_escalations(session, status=status_filter)
    return [EscalationOut.model_validate(r) for r in rows]


@router.post("/{escalation_id}/resolve", response_model=EscalationOut)
async def resolve_escalation(
    escalation_id: UUID,
    body: ResolveEscalationRequest,
    session: AsyncSession = Depends(get_db),
) -> EscalationOut:
    """Mark an escalation as handled by ``body.resolved_by``."""
    row = await escalation_service.resolve_escalation(
        session, escalation_id=escalation_id, resolved_by=body.resolved_by
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return EscalationOut.model_validate(row)
