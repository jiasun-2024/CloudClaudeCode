# Cloud Claude Code (Web)

A from-scratch web implementation of a Claude Code-like experience powered by the Python Claude Agent SDK.

## What is included

- Backend (FastAPI + SQLAlchemy + SQLite)
  - Session CRUD
  - Per-session workspace initialization
  - Streaming run endpoint (SSE)
  - Tool approval flow (including `AskUserQuestion`)
  - Runtime health endpoint for SDK/CLI diagnostics
- Frontend (React + TypeScript + Vite + Tailwind)
  - Session sidebar (create/switch/rename/delete)
  - Chat panel with streaming assistant output
  - Approval modal for tool requests

## Project layout

- `/Users/sunjia/Documents/GitProjects/CloudClaudeCode/backend`
- `/Users/sunjia/Documents/GitProjects/CloudClaudeCode/frontend`

## Backend quick start

1. Enter backend directory:

```bash
cd /Users/sunjia/Documents/GitProjects/CloudClaudeCode/backend
```

2. Create environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

3. Run API server:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend creates:

- `backend/data/app.db` (SQLite)
- `backend/workspaces/<session_id>/...` per session

Each workspace is initialized with:

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `.claude/skills/`
- `.claude/agents/`
- `.claude/commands/`

### Runtime caveat

If Claude Code CLI is not installed on this machine, API still starts, but runs emit `run_error` and `/api/runtime/health` returns `ready=false`.

## Frontend quick start

1. Enter frontend directory:

```bash
cd /Users/sunjia/Documents/GitProjects/CloudClaudeCode/frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start development server:

```bash
npm run dev
```

Frontend expects backend at `http://127.0.0.1:8000/api` by default.
You can override with `VITE_API_BASE_URL`.

## API summary

- `POST /api/sessions`
- `GET /api/sessions`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `POST /api/sessions/{session_id}/runs/stream` (SSE)
- `POST /api/runs/{run_id}/approvals/{approval_id}`
- `GET /api/runtime/health`

## Agent defaults

The run configuration uses Claude Code presets and filesystem loading:

- `tools={"type":"preset","preset":"claude_code"}`
- `system_prompt={"type":"preset","preset":"claude_code"}`
- `setting_sources=["user","project","local"]`
- `permission_mode="default"`
- per-session `cwd` workspace
- `resume=<sdk_session_id>` for multi-turn continuity
