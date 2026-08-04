from fastapi import APIRouter

from hr_chatbot.api.v1.endpoints import policy_chat

router = APIRouter()

router.include_router(policy_chat.router, tags=["Policy Chat"])
