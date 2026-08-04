# Internal HR Policy Chatbot

FastAPI service that orchestrates LLM workflows with [LangGraph](https://github.com/langchain-ai/langgraph).
Endpoints are versioned under `/api/v1`; the app object is `hr_chatbot.main:app`.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

This creates a local `.venv` and installs dependencies from `uv.lock`.

## Configuration

Settings are loaded from a `.env` file in the project root (see
`src/hr_chatbot/core/config.py` for the full list). Create one with at least:

```bash
# required
PROJECT_API_KEY=changeme        # sent by clients as the `x-api-key` header

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=

# LLM provider keys — at least one is needed depending on which
# model tier a workflow calls
GOOGLE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# optional (defaults shown)
PROJECT_NAME=HR Policy Chatbot
VERSION=0.1.0
DEBUG=false
ENVIRONMENT=development
API_V1_STR=/api/v1
LOG_LEVEL=INFO
LOG_FORMAT=json
```

`PROJECT_API_KEY` and the four `LANGSMITH_*` vars have no default — the app
won't start without them.

## Running the API

```bash
uv run uvicorn hr_chatbot.main:app --reload
```

- `GET /health` → `{"status": "ok"}`
- `GET /` → service name + version
- Everything under `API_V1_STR` (default `/api/v1`) requires an
  `x-api-key: <PROJECT_API_KEY>` header.
- Interactive docs: `/docs` and `/redoc` (FastAPI defaults).

## Tests

```bash
uv run pytest
```

Layers: `tests/unit`, `tests/integration`, `tests/e2e`. Tests under
`tests/e2e` (or anything else that calls a real model API) cost money —
run those yourself rather than as part of routine iteration.

## Lint / format

```bash
uv run ruff check .
uv run ruff format .
```

## Adding a dependency

```bash
uv add <package>          # or: uv add --dev <package>
```

Commit the updated `uv.lock` alongside the change.
