# Claude Code Web (from scratch)

一个基于 Claude Agent SDK (Python) 的 Web 版 Claude Code 原型。

## 技术栈

- Backend: FastAPI + Python Claude Agent SDK
- Frontend: React + TypeScript + Vite
- 通信: HTTP + SSE (流式响应)

## 已实现能力

- 基础会话管理（创建会话、切换会话、查看历史消息）
- 对话流式输出（实时文本增量）
- 后端默认工作区初始化：
  - `backend/workspaces/default/CLAUDE.md`
  - `backend/workspaces/default/.claude/skills/*/SKILL.md`
  - `backend/workspaces/default/.claude/agents/*.md`
  - `backend/workspaces/default/.claude/commands/*.md`
- Agent 选项按文档配置：
  - `tools={"type":"preset","preset":"claude_code"}`
  - `system_prompt={"type":"preset","preset":"claude_code"}`
  - `setting_sources=["user","project","local"]`
  - 通过 `resume` 延续 SDK 会话

## 目录结构

- `/backend`: FastAPI 服务
- `/frontend`: React 前端
- `/ClaudeAgentSDK-docs`: 你提供的官方文档

## 运行方式

### 1) 启动后端

```bash
cd /Users/sunjia/Documents/GitProjects/CloudClaudeCode/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### 2) 启动前端

```bash
cd /Users/sunjia/Documents/GitProjects/CloudClaudeCode/frontend
npm install
npm run dev
```

前端默认请求 `http://localhost:8000`。

## 注意事项

- 当前机器若未安装 `claude-agent-sdk` 或 Claude Code CLI，`/api/health` 会显示 `degraded`，聊天接口会返回 503。
- 后端代码已经按你提供的最新文档接口组织，可在安装运行时依赖后直接联调。
