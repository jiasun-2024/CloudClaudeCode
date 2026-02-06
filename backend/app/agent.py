from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import ClaudeAgentOptions, query
    from claude_agent_sdk.types import StreamEvent
except Exception as exc:  # pragma: no cover - import guard for local dev
    ClaudeAgentOptions = None
    StreamEvent = None
    query = None
    SDK_IMPORT_ERROR: Exception | None = exc
else:
    SDK_IMPORT_ERROR = None


def sdk_available() -> bool:
    return SDK_IMPORT_ERROR is None


def sdk_error_message() -> str | None:
    if SDK_IMPORT_ERROR is None:
        return None
    return str(SDK_IMPORT_ERROR)


def _build_options(cwd: Path, resume: str | None) -> Any:
    if ClaudeAgentOptions is None:
        raise RuntimeError("claude-agent-sdk is not installed")

    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "tools": {"type": "preset", "preset": "claude_code"},
        "system_prompt": {"type": "preset", "preset": "claude_code"},
        "setting_sources": ["user", "project", "local"],
        "include_partial_messages": True,
        "max_turns": 30,
    }
    if resume:
        kwargs["resume"] = resume
    return ClaudeAgentOptions(**kwargs)


def _extract_text_block(block: Any) -> str:
    if isinstance(block, dict):
        if block.get("type") == "text":
            return str(block.get("text", ""))
        return ""

    text = getattr(block, "text", None)
    if isinstance(text, str):
        return text
    return ""


def _extract_assistant_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for block in content:
        text = _extract_text_block(block)
        if text:
            chunks.append(text)
    return "".join(chunks).strip()


def _extract_system_session_id(message: Any) -> str | None:
    if getattr(message, "subtype", None) != "init":
        return None

    data = getattr(message, "data", None)
    if isinstance(data, dict):
        value = data.get("session_id")
        if isinstance(value, str) and value:
            return value

    session_id = getattr(message, "session_id", None)
    if isinstance(session_id, str) and session_id:
        return session_id
    return None


async def stream_agent_events(
    *,
    prompt: str,
    cwd: Path,
    resume: str | None,
) -> AsyncIterator[dict[str, Any]]:
    if query is None:
        raise RuntimeError("claude-agent-sdk is not installed")

    options = _build_options(cwd=cwd, resume=resume)

    async for message in query(prompt=prompt, options=options):
        system_session_id = _extract_system_session_id(message)
        if system_session_id:
            yield {"type": "session_init", "sdk_session_id": system_session_id}

        if StreamEvent is not None and isinstance(message, StreamEvent):
            event = message.event or {}
            event_type = event.get("type")

            if event_type == "content_block_start":
                block = event.get("content_block") or {}
                if block.get("type") == "tool_use":
                    yield {
                        "type": "tool_use",
                        "tool_name": str(block.get("name", "unknown")),
                    }

            if event_type == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta":
                    text = str(delta.get("text", ""))
                    if text:
                        yield {"type": "assistant_delta", "text": text}
            continue

        assistant_text = _extract_assistant_text(message)
        if assistant_text:
            yield {"type": "assistant_message", "text": assistant_text}

        if hasattr(message, "subtype") and hasattr(message, "is_error"):
            payload = {
                "type": "result",
                "subtype": getattr(message, "subtype", None),
                "is_error": bool(getattr(message, "is_error", False)),
                "session_id": getattr(message, "session_id", None),
                "result": getattr(message, "result", None),
            }
            yield payload
