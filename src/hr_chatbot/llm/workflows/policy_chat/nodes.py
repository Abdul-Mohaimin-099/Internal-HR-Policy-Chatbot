"""LangGraph nodes for the policy-chat workflow (plan §3).

Topology
--------
START → triage → (safe) retrieve → respond → persist → END
               ↘ (sensitive) escalate ──────↗

Each async function is a graph node: it receives ``PolicyChatState``, performs
one concern (classify / search / draft / ticket / save), and returns a partial
state update that LangGraph merges in.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import select

from hr_chatbot.core.config import settings
from hr_chatbot.core.database import AsyncSessionLocal
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.llm.models import get_chat_llm, get_structured_llm, model_used_label
from hr_chatbot.llm.prompts import load_prompt
from hr_chatbot.llm.workflows.policy_chat.state import PolicyChatState, TriageResult
from hr_chatbot.models.conversation import Conversation, Message
from hr_chatbot.models.user import User
from hr_chatbot.rag.retriever import search
from hr_chatbot.services import audit_service, escalation_service

logger = get_logger(__name__)

# Safe copy shown when we refuse automated advice (plan §13).
_ESCALATION_REPLY = (
    "This question needs a human HR specialist. I've created a review request "
    "for the HR team, and someone will follow up with you. I can't provide "
    "automated guidance on sensitive topics like harassment, termination, or "
    "medical matters."
)


def _history_text(state: PolicyChatState, limit: int = 6) -> str:
    """Render recent messages as plain text for triage context."""
    msgs = state.get("messages") or []
    lines: list[str] = []
    for m in msgs[-limit:]:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(none)"


def _format_context(chunks: list[dict[str, Any]]) -> str:
    """Turn retrieved chunk dicts into a numbered context block for Gemini Pro."""
    if not chunks:
        return "(no relevant policy excerpts retrieved)"
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        cite = f"{c.get('filename', '?')}"
        if c.get("section"):
            cite += f" | section: {c['section']}"
        if c.get("page_number") is not None:
            cite += f" | page: {c['page_number']}"
        parts.append(
            f"[{i}] ({cite}, score={c.get('score', 0):.3f})\n{c.get('text', '')}"
        )
    return "\n\n".join(parts)


async def triage_node(state: PolicyChatState) -> dict[str, Any]:
    """Classify the question with Gemini Flash-Lite + structured Pydantic output.

    Why Flash-Lite: triage is a closed-set classification — latency and cost
    matter more than long-form generation quality. Fallbacks keep routing alive
    if the primary model ID fails (quota / allow-list / outage).
    """
    prompt = load_prompt("triage")
    # Structured output is applied per candidate inside get_structured_llm.
    structured = get_structured_llm(
        TriageResult,
        model=settings.TRIAGE_MODEL,
        temperature=0,
    )
    user_text = prompt["user_template"].format(
        question=state["user_input"],
        history=_history_text(state),
    )
    result: TriageResult = await structured.ainvoke(
        [
            SystemMessage(content=prompt["system"]),
            HumanMessage(content=user_text),
        ]
    )
    logger.info(
        "Triage category=%s sensitivity=%s needs_human=%s conf=%.2f",
        result.category,
        result.sensitivity,
        result.needs_human,
        result.confidence,
    )
    return {
        "triage": result.model_dump(),
        "messages": [HumanMessage(content=state["user_input"])],
    }


async def retrieve_node(state: PolicyChatState) -> dict[str, Any]:
    """Embed the question (gemini-embedding-2) and fetch top-k Qdrant chunks.

    Why a dedicated node: retrieval is I/O-bound and independent of generation;
    isolating it makes LangSmith traces show search latency separately.
    """
    hits = search(state["user_input"])
    chunks = [
        {
            "text": h.text,
            "score": h.score,
            "document_id": h.document_id,
            "filename": h.filename,
            "section": h.section,
            "page_number": h.page_number,
            "chunk_index": h.chunk_index,
        }
        for h in hits
    ]
    logger.info("Retrieved %s chunks for thread=%s", len(chunks), state.get("thread_id"))
    return {"retrieved_chunks": chunks}


async def respond_node(state: PolicyChatState) -> dict[str, Any]:
    """Draft a grounded answer with Gemini Flash-Lite using retrieved context.

    Flash-Lite keeps answer latency/cost low for routine policy Q&A; the
    fallback chain covers primary-model failures without dropping the request.
    """
    prompt = load_prompt("response")
    chunks = state.get("retrieved_chunks") or []
    llm = get_chat_llm(model=settings.RESPONSE_MODEL, temperature=0.2)
    user_text = prompt["user_template"].format(
        question=state["user_input"],
        context=_format_context(chunks),
    )
    ai = await llm.ainvoke(
        [
            SystemMessage(content=prompt["system"]),
            HumanMessage(content=user_text),
        ]
    )
    reply = ai.content if isinstance(ai.content, str) else str(ai.content)
    sources = [
        {
            "filename": c.get("filename"),
            "section": c.get("section"),
            "page": c.get("page_number"),
            "score": c.get("score"),
        }
        for c in chunks
    ]
    return {
        "reply": reply,
        "sources": sources,
        "escalated": False,
        "escalation_id": None,
        "messages": [AIMessage(content=reply)],
    }


async def escalate_node(state: PolicyChatState) -> dict[str, Any]:
    """Create an HR escalation ticket and return a safe refusal (no RAG advice).

    Why we skip retrieve/respond: plan §4 auto-escalation rule — high-sensitivity
    topics must never receive automated policy interpretation.
    """
    triage = state.get("triage") or {}
    async with AsyncSessionLocal() as session:
        user = await _ensure_user(session, state)
        conversation = await _ensure_conversation(session, state, user.id)
        esc = await escalation_service.create_escalation(
            session,
            conversation_id=conversation.id,
            user_id=user.id,
            category=str(triage.get("category", "general")),
            reason=str(triage.get("reasoning", "High-sensitivity query")),
        )
        await audit_service.write_audit(
            session,
            conversation_id=conversation.id,
            event_type="escalate",
            triage_result=triage,
            model_used=model_used_label(settings.TRIAGE_MODEL),
        )

    reply = _ESCALATION_REPLY
    return {
        "reply": reply,
        "sources": [],
        "escalated": True,
        "escalation_id": str(esc.id),
        "conversation_id": str(conversation.id),
        "messages": [AIMessage(content=reply)],
    }


async def persist_node(state: PolicyChatState) -> dict[str, Any]:
    """Write conversation turns + audit trail to Postgres (ADR-001).

    Why after both paths: whether we answered or escalated, HR needs a queryable
    Message row and an AuditLog entry independent of LangGraph checkpoint blobs.
    """
    triage = state.get("triage") or {}
    async with AsyncSessionLocal() as session:
        user = await _ensure_user(session, state)
        conversation = await _ensure_conversation(session, state, user.id)

        session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=state["user_input"],
                sources=None,
            )
        )
        session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=state.get("reply") or "",
                sources=state.get("sources") or [],
            )
        )
        await session.commit()

        event = "escalate" if state.get("escalated") else "respond"
        await audit_service.write_audit(
            session,
            conversation_id=conversation.id,
            event_type=event,
            triage_result=triage,
            sources_used=state.get("sources") or [],
            model_used=(
                model_used_label(settings.TRIAGE_MODEL)
                if state.get("escalated")
                else model_used_label(settings.RESPONSE_MODEL)
            ),
        )

    return {"conversation_id": str(conversation.id)}


async def _ensure_user(session, state: PolicyChatState) -> User:
    """Get-or-create the employee row from request identifiers."""
    employee_id = state.get("employee_id") or "anonymous"
    result = await session.execute(
        select(User).where(User.employee_id == employee_id)
    )
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


async def _ensure_conversation(session, state: PolicyChatState, user_id: uuid.UUID) -> Conversation:
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


def route_after_triage(state: PolicyChatState) -> str:
    """Conditional edge: send high-sensitivity / needs_human queries to escalate.

    Returning the *name* of the next node is how LangGraph wires branching.
    """
    triage = state.get("triage") or {}
    if triage.get("needs_human") or triage.get("sensitivity") == "high":
        return "escalate"
    return "retrieve"
