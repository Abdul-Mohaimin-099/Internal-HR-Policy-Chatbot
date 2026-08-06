"""Pydantic request/response schemas for versioned API endpoints.

Why this exists
---------------
FastAPI validates bodies against these models before handlers run, and the same
models drive OpenAPI docs. Keeping them separate from ORM models avoids leaking
DB internals (e.g. storage_path) to clients.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Employee question submitted to ``POST /chat``."""

    model_config = ConfigDict(populate_by_name=True)

    thread_id: str = Field(description="Stable conversation id for LangGraph memory")
    user_input: str = Field(min_length=1, description="The employee's policy question")
    employee_id: str = Field(default="anonymous", description="HRIS employee id")
    user_id: str | None = Field(default=None, description="Optional known user UUID")


class ChatResponse(BaseModel):
    """Grounded answer (or escalation acknowledgment) returned to the client."""

    model_config = ConfigDict(populate_by_name=True)

    reply: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    escalated: bool = False
    escalation_id: str | None = None
    triage: dict[str, Any] | None = None
    conversation_id: str | None = None
    thread_id: str


# Backwards-compatible aliases for the old single-node endpoint names.
PolicyChatInput = ChatRequest
PolicyChatOutput = ChatResponse


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentOut(BaseModel):
    """Indexed policy document metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    title: str
    version: str
    chunk_count: int
    uploaded_at: datetime


class DocumentUploadResponse(BaseModel):
    """Result of a successful upload + ingest."""

    document: DocumentOut
    message: str = "Document ingested and indexed"


class ReindexRequest(BaseModel):
    """Optional body for ``POST /documents/reindex``."""

    document_id: UUID | None = None  # None → reindex all known storage_paths


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    sources: list[Any] | dict[str, Any] | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    thread_id: str
    started_at: datetime
    last_message_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Escalations
# ---------------------------------------------------------------------------


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    user_id: UUID
    category: str
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class ResolveEscalationRequest(BaseModel):
    resolved_by: str = Field(min_length=1, description="HR staff identifier")
