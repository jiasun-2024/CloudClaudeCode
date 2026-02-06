from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def build_event(*, event_type: str, run_id: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type,
        "runId": run_id,
        "sessionId": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


def encode_sse(event: dict[str, Any]) -> str:
    data = json.dumps(event, ensure_ascii=False)
    return f"event: {event['type']}\ndata: {data}\n\n"
