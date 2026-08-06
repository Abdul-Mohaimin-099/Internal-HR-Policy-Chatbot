"""Chat model factory with primary + Flash-Lite fallbacks.

Why this exists
---------------
Google model quotas, regional outages, or project allow-lists can fail a
single model ID mid-request. Wrapping the primary chat model with LangChain
``with_fallbacks`` keeps triage/respond working when the preferred Flash-Lite
model is unavailable, without changing node logic.
"""

from __future__ import annotations

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger

logger = get_logger(__name__)


def _chat_model(model: str, *, temperature: float) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
    )


def _fallback_ids(primary: str) -> list[str]:
    """Ordered fallbacks, excluding the primary so we never retry the same ID."""
    return [m for m in settings.llm_fallback_models if m != primary]


def get_chat_llm(*, model: str, temperature: float = 0.0) -> Runnable:
    """Return a chat model that tries ``model``, then configured Flash-Lite fallbacks."""
    primary = _chat_model(model, temperature=temperature)
    fallbacks = [_chat_model(m, temperature=temperature) for m in _fallback_ids(model)]
    if not fallbacks:
        return primary
    logger.info("Chat LLM primary=%s fallbacks=%s", model, _fallback_ids(model))
    return primary.with_fallbacks(fallbacks)


def get_structured_llm(
    schema: type[BaseModel],
    *,
    model: str,
    temperature: float = 0.0,
) -> Runnable:
    """Like ``get_chat_llm`` but each candidate uses structured Pydantic output.

    Structured output must be applied *per* model before ``with_fallbacks`` —
    ``RunnableWithFallbacks`` does not expose ``with_structured_output``.
    """
    primary = _chat_model(model, temperature=temperature).with_structured_output(schema)
    fallbacks = [
        _chat_model(m, temperature=temperature).with_structured_output(schema)
        for m in _fallback_ids(model)
    ]
    if not fallbacks:
        return primary
    logger.info(
        "Structured LLM primary=%s fallbacks=%s schema=%s",
        model,
        _fallback_ids(model),
        schema.__name__,
    )
    return primary.with_fallbacks(fallbacks)


def model_used_label(primary: str) -> str:
    """Audit label: primary plus configured fallbacks for ops visibility."""
    fbs = _fallback_ids(primary)
    if not fbs:
        return primary
    return f"{primary} (fallbacks: {', '.join(fbs)})"
