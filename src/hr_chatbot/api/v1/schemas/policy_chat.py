from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class PolicyChatInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    thread_id: str
    user_input: str

class PolicyChatOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    response: str
