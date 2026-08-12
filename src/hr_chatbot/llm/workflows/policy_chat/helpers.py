"""Shared DB helpers for policy-chat nodes and tools."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hr_chatbot.models.conversation import Conversation
from hr_chatbot.models.user import User


async def ensure_user(session, state: dict) -> User:
    """Get-or-create the employee row from request identifiers."""
    employee_id = state.get("employee_id") or "anonymous"
    result = await session.execute(select(User).where(User.employee_id == employee_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        employee_id=employee_id,
        name=employee_id,
        email=f"{employee_id}@example.com",
        role="employee",
    )
    # Honour an explicit UUID if the client already knows the user id.
    if state.get("user_id"):
        try:
            user.id = uuid.UUID(state["user_id"])
        except ValueError:
            pass
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def ensure_conversation(session, state: dict, user_id: uuid.UUID) -> Conversation:
    """Get-or-create the Conversation row keyed by LangGraph ``thread_id``."""
    thread_id = state.get("thread_id") or str(uuid.uuid4())
    result = await session.execute(
        select(Conversation).where(Conversation.thread_id == thread_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation
    conversation = Conversation(user_id=user_id, thread_id=thread_id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation
