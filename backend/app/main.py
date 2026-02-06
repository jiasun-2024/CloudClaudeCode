from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent import sdk_available, sdk_error_message, stream_agent_events
from .models import (
    ChatMessage,
    CreateSessionRequest,
    HealthResponse,
    MessageListResponse,
    MessageRole,
    SendMessageRequest,
    SessionSummary,
    utc_now_iso,
)
from .session_store import SessionStore
from .workspace import WorkspaceManager

BASE_DIR = Path(__file__).resolve().parents[1]
WORKSPACES_DIR = BASE_DIR / "workspaces"
DATA_FILE = BASE_DIR / "data" / "sessions.json"

workspace_manager = WorkspaceManager(WORKSPACES_DIR)
default_workspace = workspace_manager.ensure_default_workspace()
store = SessionStore(DATA_FILE)

app = FastAPI(title="Claude Code Web Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    if sdk_available():
        return HealthResponse(status="ok", sdk_available=True)

    return HealthResponse(
        status="degraded",
        sdk_available=False,
        sdk_error=sdk_error_message(),
    )


@app.get("/api/sessions", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    return await store.list_sessions()


@app.post("/api/sessions")
async def create_session(payload: CreateSessionRequest) -> dict[str, str]:
    title = (payload.title or "New Session").strip() or "New Session"
    session = await store.create_session(title=title, workspace=str(default_workspace))
    return {"id": session.id, "title": session.title}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@app.get("/api/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(session_id: str) -> MessageListResponse:
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return MessageListResponse(session_id=session_id, messages=session.messages)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/sessions/{session_id}/messages/stream")
async def stream_message(session_id: str, payload: SendMessageRequest) -> StreamingResponse:
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not sdk_available():
        raise HTTPException(status_code=503, detail=f"SDK unavailable: {sdk_error_message()}")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    user_message = ChatMessage(
        id=str(uuid4()),
        role=MessageRole.USER,
        content=content,
        created_at=utc_now_iso(),
    )
    await store.append_message(session_id, user_message)

    async def event_stream():
        yield _sse("user_message", user_message.model_dump(mode="json"))

        sdk_session_id = session.sdk_session_id

        try:
            async for event in stream_agent_events(
                prompt=content,
                cwd=Path(session.workspace),
                resume=sdk_session_id,
            ):
                event_type = event.get("type")

                if event_type == "session_init":
                    sdk_session_id = str(event["sdk_session_id"])
                    await store.set_sdk_session_id(session_id, sdk_session_id)
                    yield _sse("session_init", {"sdk_session_id": sdk_session_id})
                    continue

                if event_type == "assistant_message":
                    assistant_message = ChatMessage(
                        id=str(uuid4()),
                        role=MessageRole.ASSISTANT,
                        content=str(event.get("text", "")),
                        created_at=utc_now_iso(),
                    )
                    await store.append_message(session_id, assistant_message)
                    yield _sse(
                        "assistant_message",
                        assistant_message.model_dump(mode="json"),
                    )
                    continue

                if event_type == "assistant_delta":
                    yield _sse("assistant_delta", {"text": event.get("text", "")})
                    continue

                if event_type == "tool_use":
                    yield _sse("tool_use", {"tool_name": event.get("tool_name", "")})
                    continue

                if event_type == "result":
                    result_session_id = event.get("session_id")
                    if isinstance(result_session_id, str) and result_session_id:
                        await store.set_sdk_session_id(session_id, result_session_id)
                    yield _sse(
                        "result",
                        {
                            "subtype": event.get("subtype"),
                            "is_error": event.get("is_error", False),
                            "result": event.get("result"),
                        },
                    )

            yield _sse("done", {"ok": True})
        except Exception as exc:
            error_message = ChatMessage(
                id=str(uuid4()),
                role=MessageRole.SYSTEM,
                content=f"Agent error: {exc}",
                created_at=utc_now_iso(),
            )
            await store.append_message(session_id, error_message)
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
