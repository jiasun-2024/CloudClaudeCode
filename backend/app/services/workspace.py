from pathlib import Path

DEFAULT_CLAUDE_MD = """# CLAUDE.md

## Project Mission
You are the coding agent for this workspace. Build features safely and explain tradeoffs.

## Guardrails
- Prefer small, testable changes.
- Keep files readable and well-structured.
- If a command is risky, explain the risk before proceeding.

## Collaboration Style
- Summarize the plan briefly before large refactors.
- Include validation steps and expected outcomes.
"""

DEFAULT_SKILL = """---
name: workspace-onboarding
description: Use when users ask what this workspace supports or how to get started.
---

# Workspace Onboarding Skill

When invoked:
1. Explain the available directories.
2. Mention chat session persistence and slash command support.
3. Give one concrete next step.
"""

DEFAULT_AGENT = """---
name: reviewer
description: Use for code review, risk analysis, and release readiness checks.
---

You are a focused code reviewer.
Priorities:
1. correctness
2. security
3. maintainability

Return findings ordered by severity with file references.
"""

DEFAULT_COMMAND = """Summarize the current repository status, open risks, and next implementation step in 5 bullet points."""


def bootstrap_workspace(base_dir: Path, session_id: str) -> Path:
    workspace = base_dir / session_id
    workspace.mkdir(parents=True, exist_ok=True)

    claude_dir = workspace / ".claude"
    skills_dir = claude_dir / "skills" / "workspace-onboarding"
    agents_dir = claude_dir / "agents"
    commands_dir = claude_dir / "commands"

    skills_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    commands_dir.mkdir(parents=True, exist_ok=True)

    _write_if_missing(workspace / "CLAUDE.md", DEFAULT_CLAUDE_MD)
    _write_if_missing(skills_dir / "SKILL.md", DEFAULT_SKILL)
    _write_if_missing(agents_dir / "reviewer.md", DEFAULT_AGENT)
    _write_if_missing(commands_dir / "project-status.md", DEFAULT_COMMAND)

    return workspace


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
