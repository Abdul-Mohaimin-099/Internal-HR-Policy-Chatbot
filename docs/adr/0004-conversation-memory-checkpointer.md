# ADR 0004 — Conversation memory via LangGraph checkpointer

## Status

Accepted

## Context

Multi-turn conversations need graph state continuity, while HR also needs
clean, queryable message history for audit.

## Decision

- Short-term memory: LangGraph checkpointer keyed by `thread_id`.
- Long-term / audit history: `conversations` + `messages` tables.
- Embeddings remain in Qdrant; relational rows keep `qdrant_point_id` links.

## Consequences

- Clients must reuse `thread_id` across turns for memory.
- Checkpoint blobs are not used for reporting (see ADR-001).
- Persist node writes Message rows after every path (respond or escalate).
