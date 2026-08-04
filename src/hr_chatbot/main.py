from fastapi import Depends, FastAPI, logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from hr_chatbot.core.config import settings
from hr_chatbot.core.logging_config import get_logger, setup_logging
from hr_chatbot.core.security import require_api_key
from hr_chatbot.api.v1.router import router as api_v1_router

setup_logging()
logger = get_logger(__name__)

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # app.add_middleware(GZipMiddleware, minimum_size=1000)
    # app.add_middleware(BaseHTTPMiddleware, dispatch=_add_process_time_header)

    # register_exception_handlers(app)

    @app.get("/")
    async def root():
        logger.info("Someone entered into the project link")
        return {"service": settings.PROJECT_NAME, "version": settings.VERSION}

    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    app.include_router(
        api_v1_router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(require_api_key)],
    )
    
    return app

app = create_application()
