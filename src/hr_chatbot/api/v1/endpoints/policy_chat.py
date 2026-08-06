"""``POST /chat`` — submit a policy question through the LangGraph workflow.

Why this endpoint
-----------------
This is the employee-facing entry point (plan §6). It compiles the graph with
an in-memory checkpointer by default (swap in Postgres via ``checkpointer.py``
when the DB is available), invokes triage→retrieve|escalate, and returns
reply + sources + escalation status in one response.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from hr_chatbot.api.v1.schemas import ChatRequest, ChatResponse
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.llm.checkpointer import memory_checkpointer
from hr_chatbot.llm.workflows.policy_chat.graph import policy_chat_graph

logger = get_logger(__name__)
router = APIRouter()

# Compile once at import with an in-process checkpointer so multi-turn
# ``thread_id`` memory works within a single worker without requiring Postgres
# to be up at boot. For durable memory across restarts, compile with
# ``postgres_checkpointer`` inside the app lifespan instead.
_compiled = policy_chat_graph.compile_graph(checkpointer=memory_checkpointer())


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """Run one turn of the policy-chat graph for ``body.thread_id``."""
    state = {
        "user_input": body.user_input,
        "thread_id": body.thread_id,
        "employee_id": body.employee_id,
        "user_id": body.user_id or "",
    }
    # LangGraph reads thread_id from configurable to load/save checkpoints.
    config = {"configurable": {"thread_id": body.thread_id}}
    try:
        result = await _compiled.ainvoke(state, config=config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat workflow failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Policy chat workflow failed: {exc}",
        ) from exc

    return ChatResponse(
        reply=result.get("reply") or "",
        sources=result.get("sources") or [],
        escalated=bool(result.get("escalated")),
        escalation_id=result.get("escalation_id"),
        triage=result.get("triage"),
        conversation_id=result.get("conversation_id"),
        thread_id=body.thread_id,
    )


# Keep the old path working so existing clients don't break during migration.
@router.post("/policy-chat/chatbot", response_model=ChatResponse, include_in_schema=False)
async def policy_chatbot_legacy(body: ChatRequest) -> ChatResponse:
    """Deprecated alias for ``POST /chat``."""
    return await chat(body)
