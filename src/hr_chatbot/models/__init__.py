"""ORM models package.

Import every model here so ``Base.metadata`` is fully populated when Alembic
runs ``env.py``. Without these side-effect imports, new tables would be
invisible to ``alembic revision --autogenerate``.
"""

from hr_chatbot.models.audit import AuditLog
from hr_chatbot.models.conversation import Conversation, Message
from hr_chatbot.models.document import DocumentChunk, PolicyDocument
from hr_chatbot.models.escalation import Escalation
from hr_chatbot.models.user import User

__all__ = [
    "User",
    "Conversation",
    "Message",
    "PolicyDocument",
    "DocumentChunk",
    "Escalation",
    "AuditLog",
]
