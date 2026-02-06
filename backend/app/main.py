from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from .agent import AgentRunner, SDK_AVAILABLE
from .approvals import ApprovalBroker
from .config import settings
from .db import SessionLocal, get_db, init_db
from .models import ApprovalModel, MessageModel, SessionModel
from .schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ChatMessage,
    CreateSessionRequest,
    CreateSessionResponse,
    RenameSessionRequest,
    RunStreamRequest,
    RuntimeHealthResponse,
    SessionSummary,
)
from .workspaces import initialize_workspace, remove_workspace

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.workspaces_root.mkdir(parents=True, exist_ok=True)

approvals = ApprovalBroker()
agent_runner = AgentRunner(session_factory=SessionLocal, settings=settings, approvals=approvals)


def _schedule_workspace_cleanup_retry(session_id: str, workspace_path: str) -> None:
    async def retry_worker() -> None:
        for _ in range(3):
            await asyncio.sleep(2)
            with SessionLocal() as db:
                session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
                if session is None or session.status != "deleting_failed":
                    return
                try:
                    remove_workspace(workspace_path)
                except Exception:
                    continue
                db.delete(session)
                db.commit()
                return

    try:
        asyncio.get_running_loop().create_task(retry_worker())
    except RuntimeError:
        pass


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post(f"{settings.api_prefix}/sessions", response_model=CreateSessionResponse)
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db)) -> CreateSessionResponse:
    session_id = str(uuid4())
    title = payload.title or f"Session {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}"

    workspace = initialize_workspace(settings.workspaces_root, session_id)

    model = SessionModel(
        id=session_id,
        title=title,
        workspace_path=str(workspace.resolve()),
        status="active",
    )
    db.add(model)
    db.commit()

    return CreateSessionResponse(
        id=model.id,
        title=model.title,
        workspace_path=model.workspace_path,
        created_at=model.created_at,
    )


@app.get(f"{settings.api_prefix}/sessions", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db)) -> list[SessionSummary]:
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    return [
        SessionSummary(
            id=s.id,
            title=s.title,
            workspace_path=s.workspace_path,
            sdk_session_id=s.sdk_session_id,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@app.patch(f"{settings.api_prefix}/sessions/{{session_id}}", response_model=SessionSummary)
def rename_session(session_id: str, payload: RenameSessionRequest, db: Session = Depends(get_db)) -> SessionSummary:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = payload.title
    session.updated_at = datetime.now(UTC)
    db.commit()

    return SessionSummary(
        id=session.id,
        title=session.title,
        workspace_path=session.workspace_path,
        sdk_session_id=session.sdk_session_id,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@app.delete(f"{settings.api_prefix}/sessions/{{session_id}}", status_code=204)
def delete_session(session_id: str, db: Session = Depends(get_db)) -> Response:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        remove_workspace(session.workspace_path)
    except Exception as exc:  # pragma: no cover - filesystem edge case
        session.status = "deleting_failed"
        session.updated_at = datetime.now(UTC)
        db.commit()
        _schedule_workspace_cleanup_retry(session.id, session.workspace_path)
        raise HTTPException(status_code=500, detail=f"Failed to remove workspace: {exc}") from exc

    db.delete(session)
    db.commit()
    return Response(status_code=204)


@app.get(f"{settings.api_prefix}/sessions/{{session_id}}/messages", response_model=list[ChatMessage])
def list_messages(session_id: str, db: Session = Depends(get_db)) -> list[ChatMessage]:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    return [
        ChatMessage(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            kind=m.kind,
            content_json=m.content_json,
            created_at=m.created_at,
        )
        for m in messages
    ]


@app.post(f"{settings.api_prefix}/sessions/{{session_id}}/runs/stream")
async def stream_run(session_id: str, payload: RunStreamRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stream = agent_runner.stream_run(session_id=session_id, prompt=payload.prompt, model=payload.model)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(f"{settings.api_prefix}/runs/{{run_id}}/approvals/{{approval_id}}", response_model=ApprovalDecisionResponse)
async def resolve_approval(
    run_id: str,
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    approval = db.query(ApprovalModel).filter(ApprovalModel.id == approval_id, ApprovalModel.run_id == run_id).first()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval is no longer pending")

    ok = await agent_runner.resolve_approval(
        run_id=run_id,
        approval_id=approval_id,
        behavior=payload.behavior,
        updated_input=payload.updated_input,
        message=payload.message,
        answers=payload.answers,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Failed to resolve approval")

    return ApprovalDecisionResponse(approval_id=approval_id, run_id=run_id, status="resolved")


@app.get(f"{settings.api_prefix}/runtime/health", response_model=RuntimeHealthResponse)
def runtime_health() -> RuntimeHealthResponse:
    cli_path = settings.claude_cli_path
    if cli_path:
        cli_found = Path(cli_path).exists()
    else:
        cli_found = shutil.which("claude") is not None

    if not SDK_AVAILABLE and not cli_found:
        details = "claude-agent-sdk package missing and Claude CLI not found"
    elif not SDK_AVAILABLE:
        details = "claude-agent-sdk package missing"
    elif not cli_found:
        details = "Claude CLI not found"
    else:
        details = "runtime ready"

    return RuntimeHealthResponse(
        ready=SDK_AVAILABLE and cli_found,
        cli_found=cli_found,
        sdk_imported=SDK_AVAILABLE,
        details=details,
    )
