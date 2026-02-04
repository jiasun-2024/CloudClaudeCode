from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi import HTTPException

from app.models.session import ChatMessage, SessionState
from app.schemas.chat import MessageOut
from app.schemas.session import SessionDetail, SessionSummary
from app.services.agent_runtime import AgentRuntime
from app.services.workspace import bootstrap_workspace


class SessionManager:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, SessionState] = {}

    async def create_session(self, title: str) -> SessionSummary:
        session_id = str(uuid4())
        workspace = bootstrap_workspace(self.workspace_root, session_id)
        try:
            runtime = AgentRuntime(workspace_path=workspace)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        session = SessionState(
            session_id=session_id,
            title=title,
            workspace_path=workspace,
            runtime=runtime,
        )
        self.sessions[session_id] = session
        return self._to_summary(session)

    def list_sessions(self) -> list[SessionSummary]:
        ordered = sorted(self.sessions.values(), key=lambda item: item.last_active_at, reverse=True)
        return [self._to_summary(session) for session in ordered]

    def get_session(self, session_id: str) -> SessionState:
        session = self.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return session

    def get_session_detail(self, session_id: str) -> SessionDetail:
        session = self.get_session(session_id)
        return SessionDetail(
            **self._to_summary(session).model_dump(),
            slash_commands=session.slash_commands,
            messages=[self._to_message_out(msg) for msg in session.messages],
        )

    async def send_message(self, session_id: str, content: str) -> tuple[str, list[dict]]:
        session = self.get_session(session_id)

        async with session.lock:
            session.messages.append(ChatMessage(role="user", content=content))
            runtime_result = await session.runtime.ask(content)
            reply = runtime_result["reply"] or ""

            if reply:
                session.messages.append(ChatMessage(role="assistant", content=reply))

            session.slash_commands = runtime_result.get("slash_commands", session.slash_commands)
            session.last_active_at = datetime.now(timezone.utc)

            return reply, runtime_result["events"]

    async def send_message_stream(
        self,
        session_id: str,
        content: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
    ) -> str:
        session = self.get_session(session_id)

        async with session.lock:
            session.messages.append(ChatMessage(role="user", content=content))
            runtime_result = await session.runtime.ask(content, on_event=on_event)
            reply = runtime_result["reply"] or ""

            if reply:
                session.messages.append(ChatMessage(role="assistant", content=reply))

            session.slash_commands = runtime_result.get("slash_commands", session.slash_commands)
            session.last_active_at = datetime.now(timezone.utc)
            return reply

    async def delete_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        await session.runtime.shutdown()
        self.sessions.pop(session_id, None)

    def _to_summary(self, session: SessionState) -> SessionSummary:
        return SessionSummary(
            session_id=session.session_id,
            title=session.title,
            workspace_path=str(session.workspace_path),
            created_at=session.created_at,
            last_active_at=session.last_active_at,
        )

    def _to_message_out(self, message: ChatMessage) -> MessageOut:
        return MessageOut(role=message.role, content=message.content, created_at=message.created_at)
