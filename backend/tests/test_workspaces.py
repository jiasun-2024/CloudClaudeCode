from pathlib import Path

from app.workspaces import initialize_workspace


def test_initialize_workspace_creates_expected_files(tmp_path: Path) -> None:
    workspace = initialize_workspace(tmp_path, "session-123")

    assert (workspace / "CLAUDE.md").exists()
    assert (workspace / ".claude" / "settings.json").exists()
    assert (workspace / ".claude" / "settings.local.json").exists()
    assert (workspace / ".claude" / "skills").is_dir()
    assert (workspace / ".claude" / "agents").is_dir()
    assert (workspace / ".claude" / "commands").is_dir()
