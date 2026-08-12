"""Unit tests for triage routing and chunking helpers (no live LLM calls)."""

from __future__ import annotations

from hr_chatbot.llm.workflows.policy_chat.nodes import route_after_triage
from hr_chatbot.rag.ingestion import chunk_text


def test_route_after_triage_escalates_on_high_sensitivity():
    """High sensitivity must bypass RAG (plan §4.2 auto-escalation)."""
    nxt = route_after_triage(
        {
            "user_input": "I was harassed",
            "triage": {
                "category": "conduct",
                "sensitivity": "high",
                "needs_human": False,
                "reasoning": "harassment",
                "confidence": 0.9,
            },
        }
    )
    assert nxt == "escalate"


def test_route_after_triage_escalates_when_needs_human():
    nxt = route_after_triage(
        {
            "user_input": "Am I being fired?",
            "triage": {
                "category": "termination",
                "sensitivity": "medium",
                "needs_human": True,
                "reasoning": "personal judgment",
                "confidence": 0.8,
            },
        }
    )
    assert nxt == "escalate"


def test_route_after_triage_safe_goes_to_policy_answer():
    nxt = route_after_triage(
        {
            "user_input": "How many sick days?",
            "triage": {
                "category": "leave",
                "sensitivity": "low",
                "needs_human": False,
                "reasoning": "routine leave",
                "confidence": 0.95,
            },
        }
    )
    assert nxt == "policy_answer"


def test_chunk_text_produces_overlapping_chunks():
    text = ("Paid time off accrues monthly.\n\n" * 80) + "## Holidays\n" + ("Company holidays.\n" * 40)
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert all(c.text.strip() for c in chunks)
