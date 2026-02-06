from __future__ import annotations

from pathlib import Path

DEFAULT_CLAUDE_MD = """# Project Context

This workspace powers a web-based Claude Code experience.

## Working Style

- Make minimal, safe changes.
- Explain decisions concisely.
- Prefer clear diffs over broad rewrites.

## Engineering Rules

- Keep code readable and maintainable.
- Add tests when adding behavior.
- Mention unresolved risks clearly.
"""

DEFAULT_SKILL = """---
name: project-orientation
description: Understand the project structure and suggest an implementation path.
---

When invoked:
1. Inspect top-level project structure.
2. Identify the main runtime entrypoints.
3. Provide a concise implementation plan.
"""

DEFAULT_SUBAGENT = """---
description: Specialist for reviewing implementation risks and regressions.
tools: Read, Grep, Glob
model: sonnet
---

You are a review specialist.
Focus on correctness risks, regressions, and missing tests.
"""

DEFAULT_COMMAND = """---
description: Summarize current repository status
allowed-tools: Read, Glob, Grep
---

Summarize architecture, key modules, and active risks in this repository.
"""


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure_default_workspace(self) -> Path:
        workspace = self.root / "default"
        self._ensure_workspace_tree(workspace)
        return workspace

    def _ensure_workspace_tree(self, workspace: Path) -> None:
        (workspace / ".claude" / "skills" / "project-orientation").mkdir(
            parents=True,
            exist_ok=True,
        )
        (workspace / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        (workspace / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

        self._ensure_file(workspace / "CLAUDE.md", DEFAULT_CLAUDE_MD)
        self._ensure_file(
            workspace / ".claude" / "skills" / "project-orientation" / "SKILL.md",
            DEFAULT_SKILL,
        )
        self._ensure_file(
            workspace / ".claude" / "agents" / "code-reviewer.md",
            DEFAULT_SUBAGENT,
        )
        self._ensure_file(
            workspace / ".claude" / "commands" / "project-summary.md",
            DEFAULT_COMMAND,
        )

    @staticmethod
    def _ensure_file(path: Path, content: str) -> None:
        if path.exists():
            return
        path.write_text(content, encoding="utf-8")
