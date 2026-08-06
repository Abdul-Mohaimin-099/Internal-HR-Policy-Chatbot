"""Environment-driven application configuration.

Why this exists
---------------
Every secret, URL, and model ID must come from the environment so the same
codebase can run in local Docker, CI, and production without edits. Pydantic
Settings validates types at startup — the process fails fast if a required
value is missing, rather than crashing mid-request.
"""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed view of ``.env`` / process environment variables.

    ``extra="ignore"`` lets unknown keys (e.g. leftover secrets) sit in ``.env``
    without breaking startup. ``lru_cache`` on ``get_settings`` ensures we parse
    the env file once per process.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Application ---
    PROJECT_NAME: str = "HR Policy Chatbot"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    # Clients must send this value in the ``x-api-key`` header for /api/v1/*.
    PROJECT_API_KEY: str

    # --- LLM providers + model IDs ---
    # Flash-Lite primary for cost/latency; ordered fallbacks keep the graph up if
    # the preferred model is quota-limited or unavailable for the project.
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    TRIAGE_MODEL: str = "gemini-3.1-flash-lite"
    RESPONSE_MODEL: str = "gemini-3.1-flash-lite"
    # Comma-separated Flash-Lite (and compatible) IDs tried after the primary fails.
    LLM_FALLBACK_MODELS: str = "gemini-3.5-flash-lite,gemini-2.5-flash-lite"
    # Plan used text-embedding-004; we use gemini-embedding-2 as requested.
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    # Matryoshka output size — 768 balances recall quality vs Qdrant storage cost.
    EMBEDDING_DIMENSIONS: int = 768

    @property
    def llm_fallback_models(self) -> list[str]:
        """Parsed ordered fallback model IDs from ``LLM_FALLBACK_MODELS``."""
        return [m.strip() for m in self.LLM_FALLBACK_MODELS.split(",") if m.strip()]

    # --- LangSmith (observability) ---
    # When LANGSMITH_TRACING=true, LangChain auto-exports spans for every LLM call.
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "HR Policy Chatbot"

    # --- PostgreSQL ---
    # Async SQLAlchemy uses the asyncpg driver; the checkpointer needs a sync DSN too.
    DATABASE_URL: str = "postgresql+asyncpg://hr:hr@localhost:5432/hr_chatbot"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://hr:hr@localhost:5432/hr_chatbot"

    # --- Qdrant (vector store for policy chunks) ---
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_CLUSTER_ID: str | None = None
    QDRANT_COLLECTION: str = "hr_policy_chunks"

    # --- Torch / Docling (Windows) ---
    # When true, force-disable torch.compile so Docling does not need MSVC cl.exe.
    TORCHDYNAMO_DISABLE: str = "1"
    TORCH_COMPILE_DISABLE: str = "1"
    TORCHINDUCTOR_DISABLE: str = "1"

    # --- RAG tuning ---
    # ~500 tokens ≈ 2000 chars; 50-token overlap ≈ 200 chars keeps sentence context.
    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5
    # Cosine similarity floor — drop chunks that are probably off-topic.
    RETRIEVAL_SCORE_THRESHOLD: float = 0.45

    @field_validator(
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "QDRANT_API_KEY",
        "LANGSMITH_API_KEY",
        "PROJECT_API_KEY",
        mode="before",
    )
    @classmethod
    def _strip_secrets(cls, value: object) -> object:
        """Trim accidental spaces from pasted .env secrets."""
        if isinstance(value, str):
            return value.strip()
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (loads ``.env`` with override).

    ``override=True`` so a freshly edited ``.env`` wins over stale OS env vars
    during local development reloads. Also mirrors torch-disable flags into
    ``os.environ`` before Docling/torch imports.
    """
    import os

    load_dotenv(override=True)
    s = Settings()
    os.environ["TORCHDYNAMO_DISABLE"] = s.TORCHDYNAMO_DISABLE
    os.environ["TORCH_COMPILE_DISABLE"] = s.TORCH_COMPILE_DISABLE
    os.environ["TORCHINDUCTOR_DISABLE"] = s.TORCHINDUCTOR_DISABLE
    return s


settings = get_settings()
