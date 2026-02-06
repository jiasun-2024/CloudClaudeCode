from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from .approvals import ApprovalBroker, ApprovalDecision
from .config import Settings
from .events import build_event, encode_sse
from .models import ApprovalModel, MessageModel, RunModel, SessionModel

SDK_AVAILABLE = False

try:
    from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query
    from claude_agent_sdk import CLIConnectionError, CLINotFoundError
    from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

    SDK_AVAILABLE = True
except Exception:  # pragma: no cover - runtime fallback when SDK is missing
    ClaudeAgentOptions = None
    HookMatcher = None
    query = None

    class CLIConnectionError(Exception):
        pass

    class CLINotFoundError(CLIConnectionError):
        pass

    class PermissionResultAllow:  # type: ignore[override]
        def __init__(self, updated_input: dict[str, Any] | None = None) -> None:
            self.behavior = "allow"
            self.updated_input = updated_input

    class PermissionResultDeny:  # type: ignore[override]
        def __init__(self, message: str = "") -> None:
            self.behavior = "deny"
            self.message = message


DEFAULT_TOOLS_PRESET = {"type": "preset", "preset": "claude_code"}
DEFAULT_SYSTEM_PROMPT_PRESET = {"type": "preset", "preset": "claude_code"}
DEFAULT_SETTING_SOURCES = ["user", "project", "local"]


async def _noop_pre_tool_hook(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    _ = (input_data, tool_use_id, context)
    return {"continue_": True}


def build_agent_option_payload(*, cwd: str, resume: str | None, model: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tools": dict(DEFAULT_TOOLS_PRESET),
        "system_prompt": dict(DEFAULT_SYSTEM_PROMPT_PRESET),
        "setting_sources": list(DEFAULT_SETTING_SOURCES),
        "cwd": cwd,
        "permission_mode": "default",
        "include_partial_messages": True,
    }
    if resume:
        payload["resume"] = resume
    if model:
        payload["model"] = model
    return payload


def build_agent_options(
    *,
    cwd: str,
    resume: str | None,
    model: str | None,
    can_use_tool: Any,
) -> Any:
    payload = build_agent_option_payload(cwd=cwd, resume=resume, model=model)
    payload["can_use_tool"] = can_use_tool

    if HookMatcher is not None:
        payload["hooks"] = {"PreToolUse": [HookMatcher(matcher=None, hooks=[_noop_pre_tool_hook])]}
    else:
        payload["hooks"] = {"PreToolUse": [{"matcher": None, "hooks": [_noop_pre_tool_hook]}]}

    if SDK_AVAILABLE and ClaudeAgentOptions is not None:
        return ClaudeAgentOptions(**payload)
    return payload


class AgentRunner:
    def __init__(self, *, session_factory: sessionmaker[Session], settings: Settings, approvals: ApprovalBroker) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._approvals = approvals

    async def stream_run(self, *, session_id: str, prompt: str, model: str | None = None):
        run_id = self._create_run_and_user_message(session_id=session_id, prompt=prompt)
        queue: asyncio.Queue[str] = asyncio.Queue()
        done = asyncio.Event()

        worker = asyncio.create_task(
            self._execute_run(
                session_id=session_id,
                run_id=run_id,
                prompt=prompt,
                model=model,
                queue=queue,
                done=done,
            )
        )

        try:
            while True:
                if done.is_set() and queue.empty():
                    break
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.25)
                except TimeoutError:
                    continue
                yield chunk
        finally:
            await worker

    async def resolve_approval(
        self,
        *,
        run_id: str,
        approval_id: str,
        behavior: str,
        updated_input: dict[str, Any] | None,
        message: str | None,
        answers: dict[str, Any] | None,
    ) -> bool:
        decision = ApprovalDecision(
            behavior=behavior,
            updated_input=updated_input,
            message=message,
            answers=answers,
        )
        resolved = await self._approvals.resolve(approval_id=approval_id, decision=decision)
        if not resolved:
            return False

        with self._session_factory() as db:
            approval = (
                db.query(ApprovalModel)
                .filter(ApprovalModel.id == approval_id, ApprovalModel.run_id == run_id, ApprovalModel.status == "pending")
                .first()
            )
            if approval is None:
                return False
            approval.status = "resolved"
            approval.response_json = {
                "behavior": behavior,
                "updated_input": updated_input,
                "message": message,
                "answers": answers,
            }
            approval.resolved_at = datetime.now(UTC)
            db.commit()

        return True

    def _create_run_and_user_message(self, *, session_id: str, prompt: str) -> str:
        with self._session_factory() as db:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            run = RunModel(session_id=session_id, status="running")
            db.add(run)
            db.flush()

            user_message = MessageModel(
                session_id=session_id,
                role="user",
                kind="user_prompt",
                content_json={"text": prompt},
            )
            db.add(user_message)
            session.updated_at = datetime.now(UTC)
            db.commit()
            return run.id

    async def _execute_run(
        self,
        *,
        session_id: str,
        run_id: str,
        prompt: str,
        model: str | None,
        queue: asyncio.Queue[str],
        done: asyncio.Event,
    ) -> None:
        async def emit(event_type: str, payload: dict[str, Any]) -> None:
            event = build_event(event_type=event_type, run_id=run_id, session_id=session_id, payload=payload)
            await queue.put(encode_sse(event))

        await emit("run_started", {"prompt": prompt})

        try:
            if not SDK_AVAILABLE or query is None:
                raise CLINotFoundError("claude-agent-sdk or Claude Code CLI is not available")

            session = self._get_session(session_id)
            options = build_agent_options(
                cwd=session.workspace_path,
                resume=session.sdk_session_id,
                model=model or self._settings.default_model,
                can_use_tool=self._make_tool_permission_handler(session_id=session_id, run_id=run_id, emit=emit),
            )

            async for message in query(prompt=prompt, options=options):
                await self._handle_message(message=message, session_id=session_id, run_id=run_id, emit=emit)

            self._finish_run(run_id=run_id, status="completed", error=None)

        except (CLINotFoundError, CLIConnectionError) as exc:
            self._finish_run(run_id=run_id, status="error", error=str(exc))
            await emit(
                "run_error",
                {
                    "kind": "runtime_missing",
                    "message": str(exc),
                    "hint": "Install Claude Code and authenticate before running agent sessions.",
                },
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._finish_run(run_id=run_id, status="error", error=str(exc))
            await emit("run_error", {"kind": "unexpected", "message": str(exc)})
        finally:
            run = self._get_run(run_id)
            await emit("run_completed", {"status": run.status, "error": run.error})
            done.set()

    def _make_tool_permission_handler(self, *, session_id: str, run_id: str, emit: Any):
        async def can_use_tool(tool_name: str, input_data: dict[str, Any], context: Any):
            _ = context
            pending = await self._approvals.create_pending(
                run_id=run_id,
                session_id=session_id,
                tool_name=tool_name,
                input_data=input_data,
                timeout_seconds=60,
            )

            with self._session_factory() as db:
                approval = ApprovalModel(
                    id=pending.approval_id,
                    run_id=run_id,
                    tool_name=tool_name,
                    input_json=input_data,
                    status="pending",
                    expires_at=pending.expires_at,
                )
                db.add(approval)
                db.commit()

            await emit(
                "approval_required",
                {
                    "approvalId": pending.approval_id,
                    "toolName": tool_name,
                    "input": input_data,
                    "expiresAt": pending.expires_at.isoformat(),
                },
            )

            decision = await self._approvals.wait_for_decision(approval_id=pending.approval_id, timeout_seconds=60)

            if decision is None:
                with self._session_factory() as db:
                    approval = db.query(ApprovalModel).filter(ApprovalModel.id == pending.approval_id).first()
                    if approval is not None and approval.status == "pending":
                        approval.status = "expired"
                        approval.response_json = {
                            "behavior": "deny",
                            "message": "Approval timed out",
                        }
                        approval.resolved_at = datetime.now(UTC)
                        db.commit()

                await emit(
                    "approval_resolved",
                    {
                        "approvalId": pending.approval_id,
                        "status": "expired",
                        "behavior": "deny",
                    },
                )
                return PermissionResultDeny(message="Approval timed out")

            if decision.behavior == "allow":
                final_input = dict(input_data)
                if decision.updated_input:
                    final_input = decision.updated_input
                if tool_name == "AskUserQuestion" and decision.answers is not None:
                    final_input["answers"] = decision.answers

                await emit(
                    "approval_resolved",
                    {
                        "approvalId": pending.approval_id,
                        "status": "resolved",
                        "behavior": "allow",
                    },
                )
                return PermissionResultAllow(updated_input=final_input)

            deny_message = decision.message or "User denied this action"
            await emit(
                "approval_resolved",
                {
                    "approvalId": pending.approval_id,
                    "status": "resolved",
                    "behavior": "deny",
                    "message": deny_message,
                },
            )
            return PermissionResultDeny(message=deny_message)

        return can_use_tool

    async def _handle_message(self, *, message: Any, session_id: str, run_id: str, emit: Any) -> None:
        class_name = message.__class__.__name__

        if class_name == "SystemMessage" and getattr(message, "subtype", "") == "init":
            data = getattr(message, "data", {}) or {}
            sdk_session_id = data.get("session_id") or getattr(message, "session_id", None)
            if sdk_session_id:
                self._update_session_sdk_id(session_id=session_id, sdk_session_id=str(sdk_session_id))
            self._save_message(
                session_id=session_id,
                role="system",
                kind="system_init",
                content_json={"data": data},
            )
            await emit(
                "system_init",
                {
                    "sdkSessionId": sdk_session_id,
                    "slashCommands": data.get("slash_commands", []),
                    "raw": data,
                },
            )
            return

        if class_name == "StreamEvent":
            raw_event = getattr(message, "event", {}) or {}
            if raw_event.get("type") == "content_block_delta":
                delta = raw_event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        await emit("assistant_delta", {"text": text})
            return

        if class_name == "AssistantMessage":
            content = getattr(message, "content", []) or []
            text_parts: list[str] = []

            for block in content:
                if hasattr(block, "text"):
                    text_parts.append(getattr(block, "text"))
                elif hasattr(block, "name") and hasattr(block, "input"):
                    await emit(
                        "tool_use",
                        {
                            "toolName": getattr(block, "name"),
                            "input": getattr(block, "input"),
                        },
                    )
                elif hasattr(block, "tool_use_id"):
                    await emit(
                        "tool_result",
                        {
                            "toolUseId": getattr(block, "tool_use_id"),
                            "content": getattr(block, "content", None),
                            "isError": getattr(block, "is_error", False),
                        },
                    )

            if text_parts:
                text = "".join(text_parts)
                self._save_message(
                    session_id=session_id,
                    role="assistant",
                    kind="assistant_message",
                    content_json={"text": text},
                )
                await emit("assistant_message", {"text": text})
            return

        if class_name == "ResultMessage":
            payload = {
                "subtype": getattr(message, "subtype", "unknown"),
                "isError": bool(getattr(message, "is_error", False)),
                "result": getattr(message, "result", None),
                "numTurns": getattr(message, "num_turns", None),
                "totalCostUsd": getattr(message, "total_cost_usd", None),
                "sessionId": getattr(message, "session_id", None),
            }
            self._save_message(
                session_id=session_id,
                role="system",
                kind="result",
                content_json=payload,
            )
            await emit("result", payload)
            return

    def _get_session(self, session_id: str) -> SessionModel:
        with self._session_factory() as db:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            return session

    def _get_run(self, run_id: str) -> RunModel:
        with self._session_factory() as db:
            run = db.query(RunModel).filter(RunModel.id == run_id).first()
            if run is None:
                raise ValueError(f"Run not found: {run_id}")
            return run

    def _finish_run(self, *, run_id: str, status: str, error: str | None) -> None:
        with self._session_factory() as db:
            run = db.query(RunModel).filter(RunModel.id == run_id).first()
            if run is None:
                return
            run.status = status
            run.error = error
            run.finished_at = datetime.now(UTC)
            session = db.query(SessionModel).filter(SessionModel.id == run.session_id).first()
            if session is not None:
                session.updated_at = datetime.now(UTC)
            db.commit()

    def _save_message(self, *, session_id: str, role: str, kind: str, content_json: dict[str, Any]) -> None:
        with self._session_factory() as db:
            msg = MessageModel(
                session_id=session_id,
                role=role,
                kind=kind,
                content_json=content_json,
            )
            db.add(msg)
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session is not None:
                session.updated_at = datetime.now(UTC)
            db.commit()

    def _update_session_sdk_id(self, *, session_id: str, sdk_session_id: str) -> None:
        with self._session_factory() as db:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session is None:
                return
            session.sdk_session_id = sdk_session_id
            session.updated_at = datetime.now(UTC)
            db.commit()
