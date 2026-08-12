"""LangChain tools used by policy-chat subagents.

Why tools (not bare function calls)
-----------------------------------
The policy-answer and escalation subagents invoke capabilities via tool calling
(``create_agent`` loop). Graph routing still decides *which* subagent runs;
tools decide *how* retrieval / ticket creation execute inside that agent.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import tool

from hr_chatbot.core.config import settings
from hr_chatbot.core.database import AsyncSessionLocal
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.llm.models import model_used_label
from hr_chatbot.llm.workflows.policy_chat.helpers import ensure_conversation, ensure_user
from hr_chatbot.rag.retriever import search
from hr_chatbot.services import audit_service, escalation_service

logger = get_logger(__name__)


def chunks_to_context(chunks: list[dict[str, Any]]) -> str:
    """Turn retrieved chunk dicts into a numbered context block for the LLM."""
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


def hits_to_payload(hits: list[Any]) -> dict[str, Any]:
    """Normalize retriever hits into chunks / sources / context for tool output."""
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
        "context": chunks_to_context(chunks),
        "chunks": chunks,
        "sources": sources,
    }


@tool("rag_search")
def rag_search(query: str) -> str:
    """RAG tool: embed ``query`` and retrieve top-k HR policy chunks from Qdrant.

    This is the only retrieval path for grounded answers. Always call it before
    answering an employee policy question. Returns JSON with ``context``
    (numbered excerpts), ``chunks``, and ``sources`` for citations.
    """
    hits = search(query)
    payload = hits_to_payload(hits)
    logger.info("rag_search returned %s chunks", len(payload["chunks"]))
    return json.dumps(payload)


# Back-compat alias used by older call sites / docs.
search_policies = rag_search


@tool("create_escalation_ticket")
async def create_escalation_ticket(
    category: str,
    reason: str,
    employee_id: str,
    thread_id: str,
    user_id: str = "",
) -> str:
    """Create an open HR escalation ticket for a sensitive employee query.

    Returns JSON with ``escalation_id`` and ``conversation_id``. Call exactly once
    before telling the employee that a human will follow up.
    """
    state = {
        "employee_id": employee_id or "anonymous",
        "thread_id": thread_id,
        "user_id": user_id or "",
    }
    async with AsyncSessionLocal() as session:
        user = await ensure_user(session, state)
        conversation = await ensure_conversation(session, state, user.id)
        esc = await escalation_service.create_escalation(
            session,
            conversation_id=conversation.id,
            user_id=user.id,
            category=category or "general",
            reason=reason or "High-sensitivity query",
        )
        await audit_service.write_audit(
            session,
            conversation_id=conversation.id,
            event_type="escalate",
            triage_result={
                "category": category,
                "reasoning": reason,
            },
            model_used=model_used_label(settings.TRIAGE_MODEL),
        )
    result = {
        "escalation_id": str(esc.id),
        "conversation_id": str(conversation.id),
    }
    logger.info(
        "create_escalation_ticket id=%s conversation=%s",
        result["escalation_id"],
        result["conversation_id"],
    )
    return json.dumps(result)
