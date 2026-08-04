"""Logging setup helpers."""

import logging

from hr_chatbot.core.config import settings

_CONFIGURED = False


def setup_logging() -> None:
    """Configure root logging once at startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
