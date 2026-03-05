import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    agent_type: str | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    started_at: datetime
    messages: list[Any]
    agent_type: str | None
    actions_taken: list[Any]

    model_config = ConfigDict(from_attributes=True)
