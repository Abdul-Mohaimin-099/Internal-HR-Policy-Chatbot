# Internal HR Policy Chatbot

FastAPI + LangGraph service that answers employee HR-policy questions with
RAG (Gemini embeddings + Qdrant), triages sensitive topics to human HR, and
persists an auditable trail in PostgreSQL.

## Architecture (short)

```
POST /api/v1/chat
  → triage (Gemini Flash)
      ├─ safe      → retrieve (gemini-embedding-2 + Qdrant) → respond (Gemini Pro) → persist
      └─ sensitive → escalate (ticket + safe refusal) ──────────────────────────→ persist
```

Embeddings use **`gemini-embedding-2`** (768-d Matryoshka vectors), not
`text-embedding-004` from the original plan.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16 (local Docker or managed)
- Qdrant Cloud (or local Qdrant)
- Google AI API key

## Setup

```bash
uv sync
cp .env.example .env   # then fill GOOGLE_API_KEY, QDRANT_*, PROJECT_API_KEY
docker compose up -d postgres
uv run alembic upgrade head
```

Optional — index the sample policies under `docs/policies/`:

```bash
uv run python scripts/seed_policies.py
```

## Run

```bash
uv run uvicorn hr_chatbot.main:app --reload
```

- `GET /health` → `{"status": "ok"}` (public)
- `GET /` → service banner (public)
- Everything under `/api/v1` requires header `x-api-key: <PROJECT_API_KEY>`
- Interactive docs: `/docs`

## Main API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/chat` | Ask a policy question |
| POST | `/api/v1/documents/upload` | Upload + index PDF/Markdown |
| POST | `/api/v1/documents/reindex` | Rebuild vectors |
| GET | `/api/v1/documents` | List indexed docs |
| GET | `/api/v1/conversations/{user_id}` | Conversation history |
| GET | `/api/v1/escalations` | Open HR review cases |
| POST | `/api/v1/escalations/{id}/resolve` | Mark case handled |

### Chat example

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "x-api-key: changeme" \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\":\"t1\",\"employee_id\":\"E001\",\"user_input\":\"How many sick days do I get?\"}"
```

## Tests

```bash
uv run pytest
```

## Project layout

See `src/hr_chatbot/` — mirrors the implementation plan:

- `core/` — settings, auth, logging, async DB
- `models/` — SQLAlchemy ORM
- `rag/` — Docling ingest, gemini-embedding-2, Qdrant retriever
- `llm/workflows/policy_chat/` — LangGraph nodes + graph
- `llm/prompts/` — YAML prompts (ADR-002)
- `services/` — escalation + audit helpers
- `api/v1/` — versioned REST endpoints
