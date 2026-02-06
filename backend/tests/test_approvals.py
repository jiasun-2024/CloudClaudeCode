import asyncio

from app.approvals import ApprovalBroker, ApprovalDecision


async def test_approval_broker_resolve_flow() -> None:
    broker = ApprovalBroker()
    pending = await broker.create_pending(
        run_id="run-1",
        session_id="session-1",
        tool_name="Bash",
        input_data={"command": "ls"},
        timeout_seconds=5,
    )

    async def resolve() -> None:
        await asyncio.sleep(0.01)
        ok = await broker.resolve(
            approval_id=pending.approval_id,
            decision=ApprovalDecision(behavior="allow", updated_input={"command": "pwd"}),
        )
        assert ok

    task = asyncio.create_task(resolve())
    decision = await broker.wait_for_decision(approval_id=pending.approval_id, timeout_seconds=1)
    await task

    assert decision is not None
    assert decision.behavior == "allow"
    assert decision.updated_input == {"command": "pwd"}


async def test_approval_broker_timeout_returns_none() -> None:
    broker = ApprovalBroker()
    pending = await broker.create_pending(
        run_id="run-2",
        session_id="session-2",
        tool_name="Read",
        input_data={"file_path": "README.md"},
        timeout_seconds=1,
    )

    decision = await broker.wait_for_decision(approval_id=pending.approval_id, timeout_seconds=0.01)
    assert decision is None
