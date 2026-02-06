from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from .models import ChatMessage, ChatSession, SessionSummary, utc_now_iso


class SessionStore:
    def __init__(self, storage_file: Path) -> None:
        self._storage_file = storage_file
        self._storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._sessions: dict[str, ChatSession] = {}
        self._load()

    def _load(self) -> None:
        if not self._storage_file.exists():
            return

        raw = json.loads(self._storage_file.read_text(encoding="utf-8"))
        for session_data in raw.get("sessions", []):
            session = ChatSession.model_validate(session_data)
            self._sessions[session.id] = session

    def _persist_locked(self) -> None:
        payload = {
            "sessions": [session.model_dump(mode="json") for session in self._sessions.values()]
        }
        self._storage_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def list_sessions(self) -> list[SessionSummary]:
        async with self._lock:
            sessions = sorted(
                self._sessions.values(),
                key=lambda session: session.updated_at,
                reverse=True,
            )
            return [
                SessionSummary(
                    id=session.id,
                    title=session.title,
                    updated_at=session.updated_at,
                    message_count=len(session.messages),
                )
                for session in sessions
            ]

    async def create_session(self, title: str, workspace: str) -> ChatSession:
        async with self._lock:
            now = utc_now_iso()
            session = ChatSession(
                id=str(uuid4()),
                title=title,
                workspace=workspace,
                created_at=now,
                updated_at=now,
                messages=[],
            )
            self._sessions[session.id] = session
            self._persist_locked()
            return session.model_copy(deep=True)

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.model_copy(deep=True)

    async def append_message(self, session_id: str, message: ChatMessage) -> ChatMessage:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Session not found: {session_id}")
            session.messages.append(message)
            session.updated_at = utc_now_iso()
            self._persist_locked()
            return message.model_copy(deep=True)

    async def set_sdk_session_id(self, session_id: str, sdk_session_id: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Session not found: {session_id}")
            session.sdk_session_id = sdk_session_id
            session.updated_at = utc_now_iso()
            self._persist_locked()
