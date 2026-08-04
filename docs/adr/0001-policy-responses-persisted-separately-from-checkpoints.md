# ADR 0001 — Policy Responses Persisted Separately from Checkpoints

## Status

Proposed

## Context

The HR Policy Chatbot uses LangGraph checkpoints to persist conversation state.
Policy responses (the chatbot's assessment of an employee's query) need to be
queryable and auditable independently of the raw conversation history.

## Decision

Policy responses will be stored in a dedicated table/collection, separate from
the LangGraph checkpoint store.

## Consequences

- Policy responses can be queried, reported on, and audited without deserializing
  checkpoint blobs.
- The checkpoint store remains a pure conversation-state concern.
- A thin mapping (thread_id → policy_response_id) links the two.
