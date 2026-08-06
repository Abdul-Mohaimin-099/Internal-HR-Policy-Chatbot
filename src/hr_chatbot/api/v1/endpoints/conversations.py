"""Conversation history endpoint (plan §6 Phase 4).

Why this exists
---------------
Employees (and HR) need to pull prior turns without reading LangGraph
checkpoint blobs. We query the clean ``messages`` table keyed by user.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hr_chatbot.api.v1.schemas import ConversationOut
from hr_chatbot.core.database import get_db
from hr_chatbot.models.conversation import Conversation
from hr_chatbot.models.user import User

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/{user_id}", response_model=list[ConversationOut])
async def get_conversations(
    user_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    """Return all conversations (with messages) for a given user UUID."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    rows = (
        await session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.started_at.desc())
        )
    ).scalars().all()
    return [ConversationOut.model_validate(r) for r in rows]
