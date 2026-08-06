"""Async SQLAlchemy engine and session factory.

Why this exists
---------------
FastAPI endpoints are async; blocking DB drivers would stall the event loop.
``asyncpg`` + SQLAlchemy 2.0 async sessions give non-blocking Postgres access.
Each request gets its own session (via ``get_db``) so transactions stay isolated.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from hr_chatbot.core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Every table class inherits from this so Alembic can discover metadata in
    one place (``Base.metadata``) when generating migrations.
    """


# ``pool_pre_ping`` drops dead connections after idle timeouts (common on cloud Postgres).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# ``expire_on_commit=False`` keeps attribute values readable after commit —
# useful when returning ORM objects from FastAPI endpoints without re-querying.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped DB session.

    The ``async with`` block opens a session and guarantees ``close()`` even if
    the endpoint raises. Callers should ``await session.commit()`` explicitly
    when they mutate data; uncommitted work is rolled back on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
