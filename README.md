# CloudClaudeCode

一个从零搭建的 Web 版 Claude Code：
- 前端：React + TypeScript + Vite，提供对话框和基础会话管理
- 后端：FastAPI + Python Claude Agent SDK，按 Claude 官方文档方式运行 agent
- 工作区：每个会话自动初始化独立 workspace，默认包含 `CLAUDE.md`、skills、sub-agents、commands
- 实时输出：WebSocket + SDK partial messages，前端实时显示 token 增量

## 项目结构

```text
.
├── backend
│   ├── app
│   │   ├── api/routes.py
│   │   ├── core/config.py
│   │   ├── services/agent_runtime.py
│   │   ├── services/session_manager.py
│   │   └── services/workspace.py
│   ├── requirements.txt
│   └── workspaces/
├── frontend
│   ├── src
│   │   ├── App.tsx
│   │   ├── api/client.ts
│   │   └── components/
│   └── package.json
└── ClaudeAgentSDK-docs/
```

## 后端实现要点（对齐 Claude 官方 SDK 文档）

- 使用 `ClaudeSDKClient` 持续会话，而不是每轮新建 session
- 使用 Claude Code 默认配置：
  - `tools={"type":"preset","preset":"claude_code"}`
  - `system_prompt={"type":"preset","preset":"claude_code"}`
- 启用 `setting_sources=["user","project","local"]`，从文件系统加载：
  - `CLAUDE.md`
  - `.claude/skills/`
  - `.claude/agents/`
  - `.claude/commands/`
- 每个会话会创建一个独立 workspace（`backend/workspaces/<session_id>/`）
- 开启 `include_partial_messages=True` 并解析 `stream_event` 的 `text_delta` 进行实时推流

## 前端能力

- 左侧会话列表 + 新建会话
- 右侧聊天窗口
- 发送普通 prompt 或 slash command（例如 `/help`、`/compact`）
- WebSocket 流式输出（实时 token 显示）
- 展示当前会话的历史消息

## 运行方式

### 1) 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2) 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

默认访问：`http://localhost:5173`

## 接口

- REST: `POST /api/sessions`、`GET /api/sessions`、`GET /api/sessions/{session_id}`、`POST /api/sessions/{session_id}/messages`
- WebSocket: `WS /api/sessions/{session_id}/ws`，发送 `{"content":"..."}`，服务端返回 `token/init/result/done` 事件

## 重要说明

1. Claude Agent SDK 依赖 Claude Code CLI 运行时。请先按官方文档安装并认证 Claude Code。
2. 本项目暂未实现鉴权与多租户隔离，默认仅用于本地或可信环境。
3. 当前会话与消息状态保存在内存中；进程重启后会清空。workspace 文件会保留在磁盘。
