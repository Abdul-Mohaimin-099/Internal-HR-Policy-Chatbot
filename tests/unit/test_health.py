"""Unit tests for liveness / readiness health checks (no live DB / LLM / Qdrant)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hr_chatbot.core.health import (
    CheckResult,
    check_llm_config,
    check_postgres,
    check_qdrant,
    readiness_payload,
    run_readiness_checks,
)
from hr_chatbot.main import app

client = TestClient(app)


def test_live_and_health_are_public_and_simple():
    """``/health`` stays a backward-compatible alias of ``/live``."""
    for path in ("/live", "/health"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_ready_is_public_when_all_checks_pass():
    checks = {
        "postgres": CheckResult(ok=True),
        "qdrant": CheckResult(ok=True),
        "llm_config": CheckResult(ok=True),
    }
    with patch(
        "hr_chatbot.main.run_readiness_checks",
        new=AsyncMock(return_value=checks),
    ):
        resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["postgres"]["ok"] is True
    assert body["checks"]["qdrant"]["ok"] is True
    assert body["checks"]["llm_config"]["ok"] is True


def test_ready_returns_503_when_any_check_fails():
    checks = {
        "postgres": CheckResult(ok=True),
        "qdrant": CheckResult(ok=False, detail="QDRANT_URL not configured"),
        "llm_config": CheckResult(ok=True),
    }
    with patch(
        "hr_chatbot.main.run_readiness_checks",
        new=AsyncMock(return_value=checks),
    ):
        resp = client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["qdrant"] == {
        "ok": False,
        "detail": "QDRANT_URL not configured",
    }


def test_readiness_payload_aggregates_status():
    ok = readiness_payload({"a": CheckResult(ok=True), "b": CheckResult(ok=True)})
    assert ok["status"] == "ok"
    bad = readiness_payload(
        {"a": CheckResult(ok=True), "b": CheckResult(ok=False, detail="down")}
    )
    assert bad["status"] == "unavailable"
    assert bad["checks"]["b"]["detail"] == "down"


@pytest.mark.anyio
async def test_check_postgres_ok():
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("hr_chatbot.core.health.engine") as mock_engine:
        mock_engine.connect.return_value = mock_cm
        result = await check_postgres()
    assert result == CheckResult(ok=True)
    mock_conn.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_check_postgres_failure():
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    with patch("hr_chatbot.core.health.engine") as mock_engine:
        mock_engine.connect.return_value = mock_cm
        result = await check_postgres()
    assert result.ok is False
    assert result.detail is not None
    assert "refused" in result.detail.lower() or "ConnectionRefusedError" in result.detail


def test_check_qdrant_missing_url():
    with patch("hr_chatbot.core.health.settings") as mock_settings:
        mock_settings.QDRANT_URL = None
        result = check_qdrant()
    assert result == CheckResult(ok=False, detail="QDRANT_URL not configured")


def test_check_qdrant_ok():
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    with (
        patch("hr_chatbot.core.health.settings") as mock_settings,
        patch(
            "hr_chatbot.rag.retriever.get_qdrant_client",
            return_value=mock_client,
        ),
    ):
        mock_settings.QDRANT_URL = "https://qdrant.example"
        result = check_qdrant()
    assert result == CheckResult(ok=True)
    mock_client.get_collections.assert_called_once_with()


def test_check_qdrant_api_failure():
    mock_client = MagicMock()
    mock_client.get_collections.side_effect = TimeoutError("timed out")
    with (
        patch("hr_chatbot.core.health.settings") as mock_settings,
        patch(
            "hr_chatbot.rag.retriever.get_qdrant_client",
            return_value=mock_client,
        ),
    ):
        mock_settings.QDRANT_URL = "https://qdrant.example"
        result = check_qdrant()
    assert result.ok is False
    assert result.detail is not None


def test_check_llm_config_requires_api_key():
    with patch("hr_chatbot.core.health.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "  "
        mock_settings.TRIAGE_MODEL = "gemini-3.1-flash-lite"
        mock_settings.RESPONSE_MODEL = "gemini-3.1-flash-lite"
        result = check_llm_config()
    assert result == CheckResult(ok=False, detail="GOOGLE_API_KEY not configured")


def test_check_llm_config_ok():
    with patch("hr_chatbot.core.health.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "test-key"
        mock_settings.TRIAGE_MODEL = "gemini-3.1-flash-lite"
        mock_settings.RESPONSE_MODEL = "gemini-3.1-flash-lite"
        result = check_llm_config()
    assert result == CheckResult(ok=True)


@pytest.mark.anyio
async def test_run_readiness_checks_keys():
    with (
        patch(
            "hr_chatbot.core.health.check_postgres",
            new=AsyncMock(return_value=CheckResult(ok=True)),
        ),
        patch(
            "hr_chatbot.core.health.check_qdrant",
            return_value=CheckResult(ok=True),
        ),
        patch(
            "hr_chatbot.core.health.check_llm_config",
            return_value=CheckResult(ok=True),
        ),
    ):
        checks = await run_readiness_checks()
    assert set(checks) == {"postgres", "qdrant", "llm_config"}
    assert all(c.ok for c in checks.values())
