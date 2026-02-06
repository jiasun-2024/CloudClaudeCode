from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    id: str
    role: MessageRole
    content: str
    created_at: str
    meta: dict[str, str] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    title: str
    workspace: str
    created_at: str
    updated_at: str
    sdk_session_id: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionSummary(BaseModel):
    id: str
    title: str
    updated_at: str
    message_count: int


class CreateSessionRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    content: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    sdk_available: bool
    sdk_error: str | None = None


class MessageListResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
