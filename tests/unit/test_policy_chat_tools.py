"""Unit tests for policy-chat tools (mocked retrieval / no live Qdrant)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from hr_chatbot.llm.workflows.policy_chat.tools import hits_to_payload, rag_search


def test_hits_to_payload_formats_context_and_sources():
    hits = [
        SimpleNamespace(
            text="PTO accrues monthly.",
            score=0.91,
            document_id="doc-1",
            filename="leave.pdf",
            section="PTO",
            page_number=3,
            chunk_index=0,
        )
    ]
    payload = hits_to_payload(hits)
    assert payload["sources"][0]["filename"] == "leave.pdf"
    assert payload["sources"][0]["page"] == 3
    assert "PTO accrues monthly." in payload["context"]
    assert payload["chunks"][0]["document_id"] == "doc-1"


def test_rag_search_tool_returns_json_payload():
    hit = SimpleNamespace(
        text="Remote work needs manager approval.",
        score=0.88,
        document_id="doc-2",
        filename="remote.pdf",
        section="Eligibility",
        page_number=1,
        chunk_index=0,
    )
    with patch(
        "hr_chatbot.llm.workflows.policy_chat.tools.search",
        return_value=[hit],
    ) as mock_search:
        raw = rag_search.invoke("Can I work from home?")
    mock_search.assert_called_once_with("Can I work from home?")
    assert rag_search.name == "rag_search"
    data = json.loads(raw)
    assert len(data["chunks"]) == 1
    assert data["sources"][0]["filename"] == "remote.pdf"
    assert "Remote work" in data["context"]
