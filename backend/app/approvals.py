from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ApprovalDecision:
    behavior: str
    updated_input: dict[str, Any] | None = None
    message: str | None = None
    answers: dict[str, Any] | None = None


@dataclass(slots=True)
class PendingApproval:
    approval_id: str
    run_id: str
    session_id: str
    tool_name: str
    input_data: dict[str, Any]
    expires_at: datetime
    future: asyncio.Future[ApprovalDecision]


class ApprovalBroker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pending: dict[str, PendingApproval] = {}

    async def create_pending(
        self,
        *,
        run_id: str,
        session_id: str,
        tool_name: str,
        input_data: dict[str, Any],
        timeout_seconds: int = 60,
    ) -> PendingApproval:
        approval_id = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=timeout_seconds)
        pending = PendingApproval(
            approval_id=approval_id,
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            input_data=input_data,
            expires_at=expires_at,
            future=asyncio.get_running_loop().create_future(),
        )
        async with self._lock:
            self._pending[approval_id] = pending
        return pending

    async def resolve(self, approval_id: str, decision: ApprovalDecision) -> bool:
        async with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None or pending.future.done():
                return False
            pending.future.set_result(decision)
            return True

    async def wait_for_decision(self, approval_id: str, timeout_seconds: int = 60) -> ApprovalDecision | None:
        async with self._lock:
            pending = self._pending.get(approval_id)
        if pending is None:
            return None

        try:
            return await asyncio.wait_for(pending.future, timeout=timeout_seconds)
        except TimeoutError:
            return None
        finally:
            async with self._lock:
                self._pending.pop(approval_id, None)

    async def get_pending(self, approval_id: str) -> PendingApproval | None:
        async with self._lock:
            return self._pending.get(approval_id)
