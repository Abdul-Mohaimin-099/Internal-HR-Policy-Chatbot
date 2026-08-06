"""Alembic migration environment.

Why sync URL here
-----------------
Alembic's default migration runner is synchronous. We therefore use
``DATABASE_URL_SYNC`` (``postgresql+psycopg://`` — psycopg v3, already in
dependencies) even though the app itself talks asyncpg. A bare
``postgresql://`` URL makes SQLAlchemy import psycopg2, which we do not install.
Autogenerate imports all ORM models so new tables appear.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from hr_chatbot.core.config import settings
from hr_chatbot.core.database import Base

# Side-effect import: register every model on Base.metadata.
import hr_chatbot.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer Settings over the placeholder in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (CI-friendly)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
