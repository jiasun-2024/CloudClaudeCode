from __future__ import annotations

import shutil
from pathlib import Path

DEFAULT_CLAUDE_MD = """# Workspace Instructions

This workspace is managed by the web Claude Code app.

## Goals
- Keep changes focused and minimal.
- Explain tradeoffs when relevant.
- Prefer safe commands and avoid destructive operations unless asked.

## Project Structure
- `.claude/skills/`: project skills (`SKILL.md`).
- `.claude/agents/`: filesystem subagents.
- `.claude/commands/`: slash command markdown files.
"""

DEFAULT_PROJECT_SETTINGS = """{
  "permissions": {
    "mode": "default",
    "allow": [],
    "deny": []
  }
}
"""

DEFAULT_LOCAL_SETTINGS = """{
  "permissions": {
    "mode": "default",
    "allow": [],
    "deny": []
  }
}
"""


def initialize_workspace(workspaces_root: Path, session_id: str) -> Path:
    workspace = workspaces_root / session_id
    claude_dir = workspace / ".claude"

    (claude_dir / "skills").mkdir(parents=True, exist_ok=True)
    (claude_dir / "agents").mkdir(parents=True, exist_ok=True)
    (claude_dir / "commands").mkdir(parents=True, exist_ok=True)

    _write_if_missing(workspace / "CLAUDE.md", DEFAULT_CLAUDE_MD)
    _write_if_missing(claude_dir / "settings.json", DEFAULT_PROJECT_SETTINGS)
    _write_if_missing(claude_dir / "settings.local.json", DEFAULT_LOCAL_SETTINGS)

    return workspace


def remove_workspace(path: str | Path) -> None:
    target = Path(path)
    if not target.exists():
        return
    shutil.rmtree(target)


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
