"""Policy-chat graph state (owned by the outer StateGraph)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PolicyChatState(TypedDict, total=False):
    """Conversation state persisted per session (thread) by the checkpointer.

    ``messages`` accumulates the running Human/AI turns (clean text only — the
    structured ``create_agent`` runs statelessly inside the node, so nothing but
    plain messages is checkpointed). ``user_input`` is the per-turn input
    passed in as the graph input each request.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    # system_prompt: str
    user_input: str
    # model: str | None
