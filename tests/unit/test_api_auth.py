"""API contract smoke tests with FastAPI TestClient (no live LLM / DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from hr_chatbot.main import app

client = TestClient(app)


def test_root_and_health_are_public():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/live").json() == {"status": "ok"}


def test_v1_requires_api_key():
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 401


def test_v1_rejects_wrong_api_key():
    resp = client.get("/api/v1/documents", headers={"x-api-key": "wrong"})
    assert resp.status_code == 401
