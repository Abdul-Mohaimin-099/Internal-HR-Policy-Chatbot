"""Aggregate versioned API routers under ``/api/v1``."""

from fastapi import APIRouter

from hr_chatbot.api.v1.endpoints import conversations, documents, escalations, policy_chat

router = APIRouter()

router.include_router(policy_chat.router, tags=["Chat"])
router.include_router(documents.router)
router.include_router(conversations.router)
router.include_router(escalations.router)
