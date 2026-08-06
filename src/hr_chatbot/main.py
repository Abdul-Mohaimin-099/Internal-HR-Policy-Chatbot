"""FastAPI application factory.

Why a factory
-------------
``create_application()`` builds a fresh app so tests can construct isolated
instances. The module-level ``app`` is what uvicorn loads via
``hr_chatbot.main:app``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hr_chatbot.api.v1.router import router as api_v1_router
from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger, setup_logging
from hr_chatbot.core.security import require_api_key

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown hook — log boot and ensure upload directory exists."""
    from pathlib import Path

    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    logger.info(
        "Starting %s v%s env=%s",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """Wire middleware, public health routes, and the authenticated v1 API."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """Unauthenticated service banner for smoke checks."""
        return {"service": settings.PROJECT_NAME, "version": settings.VERSION}

    @app.get("/health")
    async def health():
        """Liveness probe — extended dependency checks can be added later."""
        return {"status": "ok"}

    # Everything under /api/v1 requires the shared project API key.
    app.include_router(
        api_v1_router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(require_api_key)],
    )
    return app


app = create_application()
