"""LLM orchestration package (prompts + LangGraph workflows)."""

from hr_chatbot.llm.models import get_chat_llm, get_structured_llm

__all__ = ["get_chat_llm", "get_structured_llm"]
