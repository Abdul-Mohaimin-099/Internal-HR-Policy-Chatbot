
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Environment-driven configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Application ---
    PROJECT_NAME: str = "HR Policy Chatbot"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    PROJECT_API_KEY: str

    # --- LLM providers + model IDs ---
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    LANGSMITH_TRACING: str
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    # --- Qdrant ---
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_CLUSTER_ID: str | None = None

@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (loads .env with override)."""
    load_dotenv(override=True)
    return Settings()


settings = get_settings()
