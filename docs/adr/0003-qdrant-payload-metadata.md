# ADR 0003 — Qdrant payload metadata for source tracking

## Status

Accepted

## Context

Response generation needs document name, section, and page to cite sources.
A secondary Postgres lookup per retrieved point adds latency.

## Decision

Each Qdrant point payload includes `document_id`, `filename`, `section`,
`page_number`, `chunk_index`, and `text`. The respond node cites from payload
fields directly.

## Consequences

- Citations do not require a join at query time.
- Reindex must keep payload fields in sync with Postgres `document_chunks`.
- Payload size grows slightly; acceptable for policy-scale corpora.
