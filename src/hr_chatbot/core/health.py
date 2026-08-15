"""Dependency health checks for Kubernetes-style liveness / readiness probes.

Why this exists
---------------
``/live`` only proves the process can answer HTTP. ``/ready`` proves Postgres,
Qdrant, and LLM config are usable before traffic is routed to this instance.
Checks stay lightweight: no embeddings, no Gemini chat calls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import text

from hr_chatbot.core.config import settings
from hr_chatbot.core.database import engine


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of a single dependency check."""

    ok: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for readiness responses."""
        return asdict(self)


def _short_error(exc: BaseException, *, limit: int = 160) -> str:
    """Human-readable error without dumping connection strings / secrets."""
    msg = str(exc).strip() or type(exc).__name__
    # Drop URL-like fragments that may include credentials.
    for marker in ("postgresql", "postgres://", "asyncpg", "http://", "https://"):
        if marker in msg.lower():
            return type(exc).__name__
    if len(msg) > limit:
        return msg[: limit - 3] + "..."
    return msg


async def check_postgres() -> CheckResult:
    """Verify Postgres accepts a trivial query via the shared async engine."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return CheckResult(ok=True)
    except Exception as exc:  # noqa: BLE001 — probe must never raise
        return CheckResult(ok=False, detail=_short_error(exc))


def check_qdrant() -> CheckResult:
    """Verify Qdrant is configured and reachable (list collections only)."""
    if not (settings.QDRANT_URL or "").strip():
        return CheckResult(ok=False, detail="QDRANT_URL not configured")
    try:
        from hr_chatbot.rag.retriever import get_qdrant_client

        client = get_qdrant_client()
        client.get_collections()
        return CheckResult(ok=True)
    except Exception as exc:  # noqa: BLE001 — probe must never raise
        return CheckResult(ok=False, detail=_short_error(exc))


def check_llm_config() -> CheckResult:
    """Config-only Gemini readiness (no live API call — cost/latency)."""
    if not (settings.GOOGLE_API_KEY or "").strip():
        return CheckResult(ok=False, detail="GOOGLE_API_KEY not configured")
    if not (settings.TRIAGE_MODEL or "").strip():
        return CheckResult(ok=False, detail="TRIAGE_MODEL not configured")
    if not (settings.RESPONSE_MODEL or "").strip():
        return CheckResult(ok=False, detail="RESPONSE_MODEL not configured")
    return CheckResult(ok=True)


async def run_readiness_checks() -> dict[str, CheckResult]:
    """Run all readiness checks and return a name → result map."""
    return {
        "postgres": await check_postgres(),
        "qdrant": check_qdrant(),
        "llm_config": check_llm_config(),
    }


def readiness_payload(checks: dict[str, CheckResult]) -> dict[str, Any]:
    """Build the JSON body for ``GET /ready``."""
    all_ok = all(c.ok for c in checks.values())
    return {
        "status": "ok" if all_ok else "unavailable",
        "checks": {name: result.to_dict() for name, result in checks.items()},
    }
