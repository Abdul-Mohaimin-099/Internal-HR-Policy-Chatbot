"""Unit tests for primary + Flash-Lite fallback chat model wiring."""

from __future__ import annotations

from langchain_core.runnables import RunnableWithFallbacks
from langchain_google_genai import ChatGoogleGenerativeAI

from hr_chatbot.llm import models as llm_models
from hr_chatbot.llm.models import get_chat_llm, get_structured_llm, model_used_label
from hr_chatbot.llm.workflows.policy_chat.state import TriageResult


def test_get_chat_llm_wraps_flash_lite_fallbacks(monkeypatch):
    monkeypatch.setattr(
        llm_models.settings,
        "LLM_FALLBACK_MODELS",
        "gemini-3.5-flash-lite,gemini-2.5-flash-lite",
    )
    monkeypatch.setattr(llm_models.settings, "GOOGLE_API_KEY", "test-key")

    llm = get_chat_llm(model="gemini-3.1-flash-lite", temperature=0.0)
    assert isinstance(llm, RunnableWithFallbacks)
    assert isinstance(llm.runnable, ChatGoogleGenerativeAI)
    assert llm.runnable.model == "gemini-3.1-flash-lite"
    assert [f.model for f in llm.fallbacks] == [
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash-lite",
    ]


def test_get_chat_llm_skips_duplicate_primary(monkeypatch):
    monkeypatch.setattr(
        llm_models.settings,
        "LLM_FALLBACK_MODELS",
        "gemini-3.1-flash-lite,gemini-3.5-flash-lite",
    )
    monkeypatch.setattr(llm_models.settings, "GOOGLE_API_KEY", "test-key")

    llm = get_chat_llm(model="gemini-3.1-flash-lite")
    assert isinstance(llm, RunnableWithFallbacks)
    assert [f.model for f in llm.fallbacks] == ["gemini-3.5-flash-lite"]


def test_get_chat_llm_without_fallbacks_returns_primary(monkeypatch):
    monkeypatch.setattr(llm_models.settings, "LLM_FALLBACK_MODELS", "")
    monkeypatch.setattr(llm_models.settings, "GOOGLE_API_KEY", "test-key")

    llm = get_chat_llm(model="gemini-3.1-flash-lite")
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == "gemini-3.1-flash-lite"


def test_get_structured_llm_uses_fallbacks(monkeypatch):
    monkeypatch.setattr(
        llm_models.settings,
        "LLM_FALLBACK_MODELS",
        "gemini-3.5-flash-lite",
    )
    monkeypatch.setattr(llm_models.settings, "GOOGLE_API_KEY", "test-key")

    llm = get_structured_llm(TriageResult, model="gemini-3.1-flash-lite")
    assert isinstance(llm, RunnableWithFallbacks)


def test_model_used_label_includes_fallbacks(monkeypatch):
    monkeypatch.setattr(
        llm_models.settings,
        "LLM_FALLBACK_MODELS",
        "gemini-3.5-flash-lite,gemini-2.5-flash-lite",
    )
    label = model_used_label("gemini-3.1-flash-lite")
    assert label.startswith("gemini-3.1-flash-lite")
    assert "gemini-3.5-flash-lite" in label
    assert "gemini-2.5-flash-lite" in label
