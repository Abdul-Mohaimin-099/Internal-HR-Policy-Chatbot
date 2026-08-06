"""Gemini embedding wrapper (plan §5 — uses ``gemini-embedding-2``).

Why this exists
---------------
Ingestion and query-time retrieval *must* share the same embedding model and
dimensionality; otherwise cosine similarity is meaningless. This module is the
single place that constructs ``GoogleGenerativeAIEmbeddings`` so both paths stay
aligned when we change model IDs in Settings.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Build (and cache) the shared Gemini embedding client.

    ``output_dimensionality`` uses Matryoshka Representation Learning so we can
    store 768-d vectors in Qdrant instead of the full 3072-d default — cheaper
    storage / faster search with acceptable recall for policy search.
    """
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is required to embed documents and queries "
            "with gemini-embedding-2"
        )

    logger.info(
        "Initialising embeddings model=%s dims=%s",
        settings.EMBEDDING_MODEL,
        settings.EMBEDDING_DIMENSIONS,
    )
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        output_dimensionality=settings.EMBEDDING_DIMENSIONS,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed many chunk texts (ingestion path).

    Batched by LangChain under the hood; we expose a plain function so callers
    don't need to know about the LangChain Embeddings interface.
    """
    return get_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a single employee question (retrieval path).

    Uses the query-side embedding path so any future task-type / instruction
    differences between documents and queries stay isolated here.
    """
    return get_embeddings().embed_query(text)
