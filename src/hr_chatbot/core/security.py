"""API-key authentication for the versioned API surface."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from hr_chatbot.core.config import settings

API_KEY_HEADER = "x-api-key"

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def require_api_key(api_key: str | None = Depends(_api_key_header)) -> str:
    """Reject any request whose ``x-api-key`` header is missing or wrong."""
    expected = settings.PROJECT_API_KEY

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is missing PROJECT_API_KEY configuration",
        )

    if not secrets.compare_digest(api_key or "", expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or missing {API_KEY_HEADER} header",
        )

    return api_key
