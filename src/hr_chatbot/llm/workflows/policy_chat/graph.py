"""Policy-chat outer workflow: a class-based StateGraph + module singleton.

LangGraph owns memory: the graph is compiled per request with the Postgres
checkpointer and persists only the clean Human/AI text produced by the node.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from hr_chatbot.llm.workflows.policy_chat.state import PolicyChatState
from hr_chatbot.llm.workflows.policy_chat.nodes import policyChatNode

class PolicyChatGraph(StateGraph):
    """The single-node policy-chat StateGraph (nodes/edges wired in ``__init__``)."""

    def __init__(self) -> None:
        super().__init__(PolicyChatState)
        self.add_node("policy_chat", policyChatNode)
        self.add_edge(START, "policy_chat")
        self.add_edge("policy_chat", END)

    def compile_graph(self, checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
        """Compile the graph, wiring the per-session checkpointer for memory."""
        return self.compile()


policy_chat_graph = PolicyChatGraph()
