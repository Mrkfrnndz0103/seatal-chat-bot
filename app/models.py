from typing import Any

from pydantic import BaseModel, Field


class CallbackEnvelope(BaseModel):
    event_type: str | None = None
    event: dict[str, Any] | None = None


class BotInput(BaseModel):
    user_id: str = ""
    conversation_id: str = ""
    incoming_text: str = ""
    raw_event: dict[str, Any] = Field(default_factory=dict)
