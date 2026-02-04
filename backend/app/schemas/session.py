from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import MessageOut


class SessionCreate(BaseModel):
    title: str = Field(default="New Session")


class SessionSummary(BaseModel):
    session_id: str
    title: str
    workspace_path: str
    created_at: datetime
    last_active_at: datetime


class SessionDetail(SessionSummary):
    slash_commands: list[str]
    messages: list[MessageOut]
