"""Policy-chat graph state — the TypedDict LangGraph checkpoints between nodes.

Why this exists
---------------
Each node reads/writes a shared state bag. Using an explicit TypedDict (not an
ad-hoc dict) documents the contract and lets LangGraph's ``add_messages``
reducer merge conversation turns safely under the Postgres checkpointer.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# Closed set from plan §4.1 — the triage model may not invent new categories.
PolicyCategory = Literal[
    "leave",
    "benefits",
    "remote_work",
    "payroll",
    "expenses",
    "conduct",
    "termination",
    "medical",
    "general",
]


class TriageResult(BaseModel):
    """Structured triage output forced via Pydantic / Gemini structured mode.

    ``needs_human`` plus ``sensitivity=high`` is the auto-escalation rule
    (plan §4.2) — the graph's conditional edge keys off these fields.
    """

    category: PolicyCategory
    sensitivity: Literal["low", "medium", "high"]
    needs_human: bool
    reasoning: str = Field(description="Brief justification for the classification")
    confidence: float = Field(ge=0.0, le=1.0)


class PolicyChatState(TypedDict, total=False):
    """Per-thread state persisted by the LangGraph checkpointer.

    Fields marked total=False may be absent on early nodes; later nodes fill them.
    ``messages`` uses ``add_messages`` so each node can append without clobbering
    prior Human/AI turns.
    """

    # Running conversation (clean text) — also mirrored to the Message table.
    messages: Annotated[list[AnyMessage], add_messages]
    # Fresh employee utterance for this HTTP turn.
    user_input: str
    # Client-supplied identifiers for persistence / escalation.
    thread_id: str
    user_id: str
    employee_id: str

    # Filled by triage node.
    triage: dict[str, Any]
    # Filled by policy_answer subagent (rag_search tool) — chunk dicts.
    retrieved_chunks: list[dict[str, Any]]
    # Final employee-facing reply (policy_answer or escalate path).
    reply: str
    # Citation payloads returned to the API client.
    sources: list[dict[str, Any]]
    # True when the escalate subagent / ticket tool ran.
    escalated: bool
    escalation_id: str | None
    # DB ids filled by persist node.
    conversation_id: str | None
