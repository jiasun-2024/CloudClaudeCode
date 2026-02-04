from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, description="User prompt or slash command")


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    messages: list[MessageOut]
    events: list[dict]
