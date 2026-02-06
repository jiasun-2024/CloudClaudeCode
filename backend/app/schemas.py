from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str | None = None


class SessionSummary(BaseModel):
    id: str
    title: str
    workspace_path: str
    sdk_session_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CreateSessionResponse(BaseModel):
    id: str
    title: str
    workspace_path: str
    created_at: datetime


class RenameSessionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str
    kind: str
    content_json: dict[str, Any]
    created_at: datetime


class RunStreamRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class ApprovalDecisionRequest(BaseModel):
    behavior: Literal["allow", "deny"]
    updated_input: dict[str, Any] | None = None
    message: str | None = None
    answers: dict[str, Any] | None = None


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    run_id: str
    status: str


class RuntimeHealthResponse(BaseModel):
    ready: bool
    cli_found: bool
    sdk_imported: bool
    details: str
