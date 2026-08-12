"""Unit tests for escalation human-in-the-loop schemas and auth gates."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from hr_chatbot.api.v1.endpoints.escalations import _to_detail
from hr_chatbot.api.v1.schemas import HrRespondRequest, ResolveEscalationRequest
from hr_chatbot.main import app

client = TestClient(app)


def test_resolve_request_accepts_optional_hr_message():
    body = ResolveEscalationRequest(
        resolved_by="hr.jane",
        hr_message="Please schedule a meeting with People Ops.",
    )
    assert body.resolved_by == "hr.jane"
    assert "People Ops" in (body.hr_message or "")


def test_hr_respond_request_requires_message():
    body = HrRespondRequest(responded_by="hr.jane", message="We are reviewing your case.")
    assert body.message.startswith("We are reviewing")


def test_to_detail_includes_sorted_messages_and_employee():
    now = datetime.now(timezone.utc)
    older = SimpleNamespace(
        id=uuid4(),
        role="user",
        content="I was harassed",
        sources=None,
        created_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    newer = SimpleNamespace(
        id=uuid4(),
        role="hr",
        content="HR is on it.",
        sources={"human_in_the_loop": True},
        created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    row = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        user_id=uuid4(),
        category="conduct",
        reason="harassment",
        status="open",
        created_at=now,
        resolved_at=None,
        resolved_by=None,
        conversation=SimpleNamespace(
            thread_id="thread-1",
            messages=[newer, older],
        ),
        user=SimpleNamespace(employee_id="E001"),
    )
    detail = _to_detail(row)  # type: ignore[arg-type]
    assert detail.thread_id == "thread-1"
    assert detail.employee_id == "E001"
    assert [m.role for m in detail.messages] == ["user", "hr"]
    assert detail.messages[1].content == "HR is on it."


def test_escalation_hitl_routes_require_api_key():
    eid = "00000000-0000-0000-0000-000000000001"
    assert client.get(f"/api/v1/escalations/{eid}").status_code == 401
    assert (
        client.post(
            f"/api/v1/escalations/{eid}/respond",
            json={"responded_by": "hr.jane", "message": "hello"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/v1/escalations/{eid}/resolve",
            json={"resolved_by": "hr.jane", "hr_message": "done"},
        ).status_code
        == 401
    )
