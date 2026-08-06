"""Policy-chat StateGraph wiring (plan §3.1).

Why a class-based graph
-----------------------
Keeps node/edge registration in one place, exposes ``compile_graph(checkpointer)``
so HTTP handlers can attach the Postgres checkpointer per process while tests
can compile with ``MemorySaver``.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from hr_chatbot.llm.workflows.policy_chat.nodes import (
    escalate_node,
    persist_node,
    respond_node,
    retrieve_node,
    route_after_triage,
    triage_node,
)
from hr_chatbot.llm.workflows.policy_chat.state import PolicyChatState


class PolicyChatGraph(StateGraph):
    """Full triage → retrieve/respond | escalate → persist workflow."""

    def __init__(self) -> None:
        super().__init__(PolicyChatState)

        # Register nodes — each name is what conditional edges return.
        self.add_node("triage", triage_node)
        self.add_node("retrieve", retrieve_node)
        self.add_node("respond", respond_node)
        self.add_node("escalate", escalate_node)
        self.add_node("persist", persist_node)

        # Linear entry: every request starts with classification.
        self.add_edge(START, "triage")

        # Branch on triage result (safe → RAG path, sensitive → escalate).
        self.add_conditional_edges(
            "triage",
            route_after_triage,
            {
                "retrieve": "retrieve",
                "escalate": "escalate",
            },
        )

        # Safe path: search then draft grounded answer.
        self.add_edge("retrieve", "respond")
        self.add_edge("respond", "persist")
        # Sensitive path: ticket + safe refusal, then same persist step.
        self.add_edge("escalate", "persist")
        self.add_edge("persist", END)

    def compile_graph(
        self, checkpointer: BaseCheckpointSaver | None = None
    ) -> CompiledStateGraph:
        """Compile with an optional checkpointer for multi-turn memory (ADR-004)."""
        return self.compile(checkpointer=checkpointer)


# Module-level singleton used by the API layer.
policy_chat_graph = PolicyChatGraph()
