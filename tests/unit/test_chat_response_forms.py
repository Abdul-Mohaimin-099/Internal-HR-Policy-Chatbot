"""Chat response dual-form schema tests (text + json)."""

from __future__ import annotations

from hr_chatbot.api.v1.schemas import ChatResponse


def test_chat_response_exposes_text_and_json_forms():
    resp = ChatResponse.from_turn(
        reply="PTO accrues monthly.",
        thread_id="t1",
        sources=[{"filename": "leave.pdf", "page": 1, "score": 0.9}],
        escalated=False,
        triage={"category": "leave", "sensitivity": "low"},
        conversation_id="c1",
    )
    # Form 1 — simple string
    assert resp.text == "PTO accrues monthly."
    assert resp.reply == resp.text
    # Form 2 — structured JSON object (API key: "json")
    assert resp.json_form.reply == resp.text
    assert resp.json_form.thread_id == "t1"
    assert resp.json_form.sources[0]["filename"] == "leave.pdf"
    assert resp.json_form.escalated is False
    assert resp.json_form.triage["category"] == "leave"
    dumped = resp.model_dump(by_alias=True)
    assert "text" in dumped and "json" in dumped
    assert dumped["json"]["conversation_id"] == "c1"
