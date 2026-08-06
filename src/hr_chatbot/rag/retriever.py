"""Qdrant semantic search over policy chunk embeddings (plan §5.2 / ADR-003).

Why this exists
---------------
After a query is embedded with gemini-embedding-2, we need nearest-neighbour
lookup with payload metadata (filename, section, page) so the respond node can
cite sources without a second Postgres round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger
from hr_chatbot.rag.embeddings import embed_query

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A policy snippet returned to the LangGraph respond node."""

    text: str
    score: float
    document_id: str
    filename: str
    section: str | None
    page_number: int | None
    chunk_index: int
    point_id: str


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Lazy singleton Qdrant client (cloud URL + API key from Settings)."""
    if not settings.QDRANT_URL:
        raise RuntimeError("QDRANT_URL is not configured")
    # Strip accidental leading space from .env values (common copy/paste issue).
    api_key = (settings.QDRANT_API_KEY or "").strip() or None
    return QdrantClient(url=settings.QDRANT_URL, api_key=api_key)


def ensure_collection() -> None:
    """Create the policy-chunk collection if it does not already exist.

    Cosine distance matches unit-ish Gemini embeddings. Vector size *must*
    equal ``EMBEDDING_DIMENSIONS`` or upserts fail at the Qdrant API.
    """
    client = get_qdrant_client()
    name = settings.QDRANT_COLLECTION
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return

    logger.info(
        "Creating Qdrant collection=%s size=%s",
        name,
        settings.EMBEDDING_DIMENSIONS,
    )
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(
            size=settings.EMBEDDING_DIMENSIONS,
            distance=qm.Distance.COSINE,
        ),
    )


def upsert_chunks(
    *,
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
    point_ids: list[str] | None = None,
) -> list[str]:
    """Write chunk vectors + metadata payloads into Qdrant.

    Returns the point IDs so Postgres ``document_chunks.qdrant_point_id`` can
    store the mapping for later delete/reindex.
    """
    ensure_collection()
    client = get_qdrant_client()
    ids = point_ids or [str(uuid4()) for _ in vectors]
    points = [
        qm.PointStruct(id=pid, vector=vec, payload=payload)
        for pid, vec, payload in zip(ids, vectors, payloads, strict=True)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return ids


def delete_points(point_ids: list[str]) -> None:
    """Remove vectors when a document is reindexed or deleted."""
    if not point_ids:
        return
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=qm.PointIdsList(points=point_ids),
    )


def search(query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
    """Embed ``query`` and return top-k chunks above the score threshold.

    Score filtering happens here (not in the LLM) so weak evidence never reaches
    the respond prompt — the model is instructed to refuse when the list is empty.
    """
    ensure_collection()
    client = get_qdrant_client()
    vector = embed_query(query)
    limit = top_k or settings.RETRIEVAL_TOP_K

    # qdrant-client >=1.12 replaced ``search`` with ``query_points``.
    response = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=limit,
        score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
        with_payload=True,
    )

    results: list[RetrievedChunk] = []
    for hit in response.points:
        payload = hit.payload or {}
        results.append(
            RetrievedChunk(
                text=str(payload.get("text", "")),
                score=float(hit.score or 0.0),
                document_id=str(payload.get("document_id", "")),
                filename=str(payload.get("filename", "")),
                section=payload.get("section"),
                page_number=payload.get("page_number"),
                chunk_index=int(payload.get("chunk_index", 0)),
                point_id=str(hit.id),
            )
        )
    return results
