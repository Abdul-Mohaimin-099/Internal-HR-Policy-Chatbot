"""Policy-chat subagents built with ``langchain.agents.create_agent``.

Topology (parent graph still owns routing)
-----------------------------------------
- ``policy_answer`` — tool-using agent with ``rag_search`` (RAG as a tool)
- ``escalation`` — tool-using agent with ``create_escalation_ticket``

The parent StateGraph decides which subagent runs after structured triage;
subagents never choose escalate vs answer themselves.
"""

from __future__ import annotations

from functools import lru_cache

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from hr_chatbot.core.config import settings
from hr_chatbot.llm.models import get_chat_llm
from hr_chatbot.llm.prompts import load_prompt
from hr_chatbot.llm.workflows.policy_chat.tools import (
    create_escalation_ticket,
    rag_search,
)

# Safe copy shown when we refuse automated advice (plan §13).
ESCALATION_REPLY = (
    "This question needs a human HR specialist. I've created a review request "
    "for the HR team, and someone will follow up with you. I can't provide "
    "automated guidance on sensitive topics like harassment, termination, or "
    "medical matters."
)


def build_policy_answer_agent() -> CompiledStateGraph:
    """Subagent that must run RAG via ``rag_search`` tool, then draft a grounded reply."""
    prompt = load_prompt("response")
    system = (
        prompt["system"]
        + "\n\n"
        + "You MUST call the rag_search tool (RAG retrieval over indexed HR "
        + "policies) with the employee's question before answering. Answer ONLY "
        + "using the excerpts returned by that tool. "
        + "Cite sources as [filename | section | page] when those fields exist. "
        + "If the tool returns no relevant excerpts, refuse and tell the employee "
        + "to contact HR."
    )
    return create_agent(
        get_chat_llm(model=settings.RESPONSE_MODEL, temperature=0.2),
        tools=[rag_search],
        system_prompt=system,
        name="policy_answer",
    )


def build_escalation_agent() -> CompiledStateGraph:
    """Subagent that opens an HR ticket via tool, then returns the safe refusal."""
    system = (
        "You handle sensitive HR escalations. You MUST call the "
        "create_escalation_ticket tool exactly once with the category, reason, "
        "employee_id, thread_id, and user_id provided in the user message. "
        "After the tool succeeds, reply to the employee with EXACTLY this text "
        f"and nothing else:\n\n{ESCALATION_REPLY}"
    )
    return create_agent(
        get_chat_llm(model=settings.TRIAGE_MODEL, temperature=0),
        tools=[create_escalation_ticket],
        system_prompt=system,
        name="escalation",
    )


@lru_cache
def get_policy_answer_agent() -> CompiledStateGraph:
    return build_policy_answer_agent()


@lru_cache
def get_escalation_agent() -> CompiledStateGraph:
    return build_escalation_agent()
