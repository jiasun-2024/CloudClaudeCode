from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
except ImportError:  # pragma: no cover
    ClaudeAgentOptions = None
    ClaudeSDKClient = None


class AgentRuntime:
    def __init__(self, workspace_path: Path):
        if ClaudeSDKClient is None or ClaudeAgentOptions is None:
            raise RuntimeError(
                "claude-agent-sdk is not installed. Install backend dependencies first."
            )

        self.workspace_path = workspace_path
        self.client = ClaudeSDKClient(options=self._build_options())
        self.connected = False
        self.sdk_session_id: str | None = None
        self.slash_commands: list[str] = []

    def _build_options(self) -> Any:
        return ClaudeAgentOptions(
            cwd=str(self.workspace_path),
            tools={"type": "preset", "preset": "claude_code"},
            system_prompt={"type": "preset", "preset": "claude_code"},
            setting_sources=["user", "project", "local"],
            max_turns=20,
            include_partial_messages=True,
        )

    async def ask(
        self,
        prompt: str,
        on_event: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
    ) -> dict[str, Any]:
        self.connected = True
        await self.client.query(prompt)

        events: list[dict[str, Any]] = []
        assistant_chunks: list[str] = []
        stream_chunks: list[str] = []

        async for message in self.client.receive_response():
            payload = self._message_to_dict(message)
            events.append(payload)
            await self._emit(on_event, payload)

            if payload.get("type") == "assistant":
                for text in payload.get("texts", []):
                    assistant_chunks.append(text)
            elif payload.get("type") == "stream_event" and payload.get("delta_text"):
                stream_chunks.append(payload["delta_text"])

            if payload.get("type") == "system" and payload.get("subtype") == "init":
                self.sdk_session_id = payload.get("session_id") or self.sdk_session_id
                self.slash_commands = payload.get("slash_commands", [])

        reply = "".join(stream_chunks).strip()
        if not reply:
            reply = "\n".join([chunk for chunk in assistant_chunks if chunk]).strip()

        return {
            "reply": reply,
            "events": events,
            "slash_commands": self.slash_commands,
            "sdk_session_id": self.sdk_session_id,
            "timestamp": datetime.now(timezone.utc),
        }

    async def shutdown(self) -> None:
        if self.connected:
            await self.client.disconnect()
            self.connected = False

    def _message_to_dict(self, message: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": getattr(message, "type", None),
            "subtype": getattr(message, "subtype", None),
        }

        if hasattr(message, "session_id"):
            payload["session_id"] = getattr(message, "session_id")
        if hasattr(message, "slash_commands"):
            payload["slash_commands"] = getattr(message, "slash_commands")
        if hasattr(message, "result"):
            payload["result"] = getattr(message, "result")
        if hasattr(message, "event"):
            payload["event"] = getattr(message, "event")

        content = getattr(message, "content", None)
        texts: list[str] = []
        if isinstance(content, list):
            for block in content:
                text = getattr(block, "text", None)
                if text:
                    texts.append(text)
        payload["texts"] = texts

        if payload["type"] == "assistant" and not texts and hasattr(message, "message"):
            nested_content = getattr(getattr(message, "message"), "content", None)
            if isinstance(nested_content, list):
                for block in nested_content:
                    text = getattr(block, "text", None)
                    if text:
                        texts.append(text)
                payload["texts"] = texts

        if payload["type"] == "stream_event":
            event = payload.get("event") or {}
            payload["event_type"] = event.get("type")
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    payload["delta_text"] = delta.get("text", "")

        return payload

    async def _emit(
        self,
        callback: Callable[[dict[str, Any]], Awaitable[None] | None] | None,
        payload: dict[str, Any],
    ) -> None:
        if callback is None:
            return
        result = callback(payload)
        if inspect.isawaitable(result):
            await result
