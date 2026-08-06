"""Optional LangGraph Postgres checkpointer factory (ADR-004).

Why optional
------------
Local unit tests and first boots should work even when Postgres is down.
When ``DATABASE_URL_SYNC`` is reachable we return an ``AsyncPostgresSaver``
so multi-turn ``thread_id`` memory survives process restarts.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger

logger = get_logger(__name__)


def memory_checkpointer() -> BaseCheckpointSaver:
    """In-process checkpointer — fine for single-worker demos and tests."""
    return MemorySaver()


@asynccontextmanager
async def postgres_checkpointer() -> AsyncIterator[BaseCheckpointSaver]:
    """Yield an ``AsyncPostgresSaver`` connected to ``DATABASE_URL_SYNC``.

    Falls back to ``MemorySaver`` if the Postgres checkpointer cannot start
    (missing driver, DB down, etc.) so the API remains usable.
    """
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # langgraph-checkpoint-postgres wants a libpq URL, not SQLAlchemy's
        # ``+psycopg`` dialect prefix used by Alembic.
        conn = settings.DATABASE_URL_SYNC.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        async with AsyncPostgresSaver.from_conn_string(conn) as saver:
            await saver.setup()
            logger.info("Using AsyncPostgresSaver for conversation memory")
            yield saver
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Postgres checkpointer unavailable (%s); using MemorySaver", exc
        )
        yield memory_checkpointer()
