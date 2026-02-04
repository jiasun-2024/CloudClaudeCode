from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.schemas.chat import ChatResponse, MessageCreate
from app.schemas.session import SessionCreate, SessionDetail, SessionSummary
from app.services.session_manager import SessionManager

router = APIRouter()


def get_session_manager() -> SessionManager:
    from app.main import session_manager

    return session_manager


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/sessions", response_model=SessionSummary)
async def create_session(
    payload: SessionCreate,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionSummary:
    return await manager.create_session(payload.title)


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    manager: SessionManager = Depends(get_session_manager),
) -> list[SessionSummary]:
    return manager.list_sessions()


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionDetail:
    return manager.get_session_detail(session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def chat(
    session_id: str,
    payload: MessageCreate,
    manager: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    reply, events = await manager.send_message(session_id=session_id, content=payload.content)
    detail = manager.get_session_detail(session_id)
    return ChatResponse(session_id=session_id, reply=reply, messages=detail.messages, events=events)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> None:
    await manager.delete_session(session_id)


@router.websocket("/sessions/{session_id}/ws")
async def chat_stream(websocket: WebSocket, session_id: str) -> None:
    manager = get_session_manager()
    await websocket.accept()

    try:
        manager.get_session(session_id)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "error": exc.detail})
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = await websocket.receive_json()
            content = str(data.get("content", "")).strip()
            if not content:
                await websocket.send_json({"type": "error", "error": "content is required"})
                continue

            async def on_runtime_event(payload: dict[str, Any]) -> None:
                message_type = payload.get("type")
                if message_type == "stream_event" and payload.get("delta_text"):
                    await websocket.send_json({"type": "token", "text": payload["delta_text"]})
                elif message_type == "system" and payload.get("subtype") == "init":
                    await websocket.send_json(
                        {
                            "type": "init",
                            "session_id": payload.get("session_id"),
                            "slash_commands": payload.get("slash_commands", []),
                        }
                    )
                elif message_type == "result":
                    await websocket.send_json(
                        {"type": "result", "subtype": payload.get("subtype"), "result": payload.get("result")}
                    )

            reply = await manager.send_message_stream(
                session_id=session_id,
                content=content,
                on_event=on_runtime_event,
            )
            detail = manager.get_session_detail(session_id)
            await websocket.send_json(
                {
                    "type": "done",
                    "reply": reply,
                    "messages": jsonable_encoder(detail.messages),
                    "slash_commands": detail.slash_commands,
                }
            )
    except WebSocketDisconnect:
        return
