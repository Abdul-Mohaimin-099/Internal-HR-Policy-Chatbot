"""LangGraph nodes for the policy-chat workflow (plan §3).

Topology
--------
START → triage → (safe) policy_answer → persist → END
               ↘ (sensitive) escalate ──────↗

``policy_answer`` and ``escalate`` are thin wrappers around tool-using
subagents (``create_agent``). Structured triage + conditional edges still own
routing so high-sensitivity queries never reach RAG.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from hr_chatbot.core.config import settings
from hr_chatbot.core.database import AsyncSessionLocal
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.llm.models import get_structured_llm, model_used_label
from hr_chatbot.llm.prompts import load_prompt
from hr_chatbot.llm.workflows.policy_chat.agents import (
    ESCALATION_REPLY,
    get_escalation_agent,
    get_policy_answer_agent,
)
from hr_chatbot.llm.workflows.policy_chat.helpers import ensure_conversation, ensure_user
from hr_chatbot.llm.workflows.policy_chat.state import PolicyChatState, TriageResult
from hr_chatbot.llm.workflows.policy_chat.tools import (
    create_escalation_ticket,
    rag_search,
)
from hr_chatbot.models.conversation import Message
from hr_chatbot.services import audit_service

logger = get_logger(__name__)


def _history_text(state: PolicyChatState, limit: int = 6) -> str:
    """Render recent messages as plain text for triage context."""
    msgs = state.get("messages") or []
    lines: list[str] = []
    for m in msgs[-limit:]:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(none)"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return str(content)


def _last_ai_text(messages: list[Any]) -> str:
    """Final non-tool-call AI message content from a subagent run."""
    for m in reversed(messages):
        if not isinstance(m, AIMessage):
            continue
        if getattr(m, "tool_calls", None):
            continue
        text = _message_text(m.content).strip()
        if text:
            return text
    return ""


def _tool_json_payloads(messages: list[Any], tool_name: str) -> list[dict[str, Any]]:
    """Parse JSON bodies from ToolMessages for ``tool_name``."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        name = getattr(m, "name", None) or ""
        if name and name != tool_name:
            continue
        try:
            data = json.loads(_message_text(m.content))
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


async def triage_node(state: PolicyChatState) -> dict[str, Any]:
    """Classify the question with Gemini Flash-Lite + structured Pydantic output.

    Why Flash-Lite: triage is a closed-set classification — latency and cost
    matter more than long-form generation quality. Fallbacks keep routing alive
    if the primary model ID fails (quota / allow-list / outage).
    """
    prompt = load_prompt("triage")
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


async def policy_answer_node(state: PolicyChatState) -> dict[str, Any]:
    """Run the policy-answer subagent (RAG tool: ``rag_search``).

    Isolating retrieval+generation in a ReAct-style agent keeps LangSmith traces
    tool-aware while the parent graph still owns escalate vs answer routing.
    """
    agent = get_policy_answer_agent()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": state["user_input"]}]}
    )
    messages = result.get("messages") or []

    chunks: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    # Accept current tool name and the previous alias if present in traces.
    for tool_name in ("rag_search", "search_policies"):
        for payload in _tool_json_payloads(messages, tool_name):
            chunks = payload.get("chunks") or chunks
            sources = payload.get("sources") or sources

    # Preserve retrieval even if the model skipped the RAG tool call.
    if not chunks and not sources:
        logger.warning("policy_answer agent skipped rag_search; invoking RAG tool directly")
        raw = rag_search.invoke(state["user_input"])
        payload = json.loads(raw)
        chunks = payload.get("chunks") or []
        sources = payload.get("sources") or []

    reply = _last_ai_text(messages)
    if not reply:
        reply = (
            "I couldn't find enough policy evidence to answer confidently. "
            "Please contact HR for guidance."
        )

    return {
        "reply": reply,
        "sources": sources,
        "retrieved_chunks": chunks,
        "escalated": False,
        "escalation_id": None,
        "messages": [AIMessage(content=reply)],
    }


async def escalate_node(state: PolicyChatState) -> dict[str, Any]:
    """Run the escalation subagent (tool: ``create_escalation_ticket``).

    Why we skip policy_answer: plan §4 auto-escalation rule — high-sensitivity
    topics must never receive automated policy interpretation. The employee-facing
    reply is the fixed safe refusal, not a free-form model paraphrase.
    """
    triage = state.get("triage") or {}
    employee_id = state.get("employee_id") or "anonymous"
    thread_id = state.get("thread_id") or ""
    user_id = state.get("user_id") or ""
    category = str(triage.get("category", "general"))
    reason = str(triage.get("reasoning", "High-sensitivity query"))

    agent = get_escalation_agent()
    user_msg = (
        f"category={category}\n"
        f"reason={reason}\n"
        f"employee_id={employee_id}\n"
        f"thread_id={thread_id}\n"
        f"user_id={user_id}\n"
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_msg}]})
    messages = result.get("messages") or []

    escalation_id: str | None = None
    conversation_id: str | None = None
    for payload in _tool_json_payloads(messages, "create_escalation_ticket"):
        escalation_id = payload.get("escalation_id") or escalation_id
        conversation_id = payload.get("conversation_id") or conversation_id

    if not escalation_id:
        logger.warning("escalation agent skipped create_escalation_ticket; invoking tool directly")
        raw = await create_escalation_ticket.ainvoke(
            {
                "category": category,
                "reason": reason,
                "employee_id": employee_id,
                "thread_id": thread_id,
                "user_id": user_id,
            }
        )
        payload = json.loads(raw)
        escalation_id = payload.get("escalation_id")
        conversation_id = payload.get("conversation_id")

    return {
        "reply": ESCALATION_REPLY,
        "sources": [],
        "escalated": True,
        "escalation_id": escalation_id,
        "conversation_id": conversation_id,
        "messages": [AIMessage(content=ESCALATION_REPLY)],
    }


async def persist_node(state: PolicyChatState) -> dict[str, Any]:
    """Write conversation turns + audit trail to Postgres (ADR-001).

    Why after both paths: whether we answered or escalated, HR needs a queryable
    Message row and an AuditLog entry independent of LangGraph checkpoint blobs.
    """
    triage = state.get("triage") or {}
    async with AsyncSessionLocal() as session:
        user = await ensure_user(session, state)
        conversation = await ensure_conversation(session, state, user.id)

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


def route_after_triage(state: PolicyChatState) -> str:
    """Conditional edge: send high-sensitivity / needs_human queries to escalate.

    Returning the *name* of the next node is how LangGraph wires branching.
    """
    triage = state.get("triage") or {}
    if triage.get("needs_human") or triage.get("sensitivity") == "high":
        return "escalate"
    return "policy_answer"
