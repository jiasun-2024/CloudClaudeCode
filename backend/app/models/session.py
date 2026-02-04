from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionState:
    session_id: str
    title: str
    workspace_path: Path
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages: list[ChatMessage] = field(default_factory=list)
    slash_commands: list[str] = field(default_factory=list)
    runtime: Any = None
    lock: Lock = field(default_factory=Lock)
