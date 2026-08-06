"""Add gen_random_uuid() defaults on primary keys.

Revision ID: 0002_uuid_defaults
Revises: 0001_initial
Create Date: 2026-08-06

pgAdmin / raw SQL inserts do not run SQLAlchemy's Python uuid.uuid4() default,
so INSERT INTO users (...) without id used to fail with NOT NULL on id.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002_uuid_defaults"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "users",
    "policy_documents",
    "conversations",
    "document_chunks",
    "messages",
    "escalations",
    "audit_logs",
)


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT")
