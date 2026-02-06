import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createSession,
  deleteSession,
  listMessages,
  listSessions,
  renameSession,
  streamRun,
  submitApproval,
} from "./api";
import { ApprovalModal } from "./components/ApprovalModal";
import { Composer } from "./components/Composer";
import { MessageList } from "./components/MessageList";
import { SessionSidebar } from "./components/SessionSidebar";
import { useAppStore } from "./store";
import type { AgentStreamEvent, ChatMessage } from "./types";

function makeLocalMessage(sessionId: string, role: string, kind: string, content: Record<string, unknown>): ChatMessage {
  return {
    id: `local-${Math.random().toString(36).slice(2)}`,
    session_id: sessionId,
    role,
    kind,
    content_json: content,
    created_at: new Date().toISOString(),
  };
}

export default function App() {
  const queryClient = useQueryClient();

  const activeSessionId = useAppStore((state) => state.activeSessionId);
  const messagesBySession = useAppStore((state) => state.messagesBySession);
  const liveAssistantBySession = useAppStore((state) => state.liveAssistantBySession);
  const pendingApprovals = useAppStore((state) => state.pendingApprovals);
  const isStreaming = useAppStore((state) => state.isStreaming);

  const setActiveSession = useAppStore((state) => state.setActiveSession);
  const setMessages = useAppStore((state) => state.setMessages);
  const appendMessage = useAppStore((state) => state.appendMessage);
  const appendAssistantDelta = useAppStore((state) => state.appendAssistantDelta);
  const clearLiveAssistant = useAppStore((state) => state.clearLiveAssistant);
  const setStreaming = useAppStore((state) => state.setStreaming);
  const addPendingApproval = useAppStore((state) => state.addPendingApproval);
  const removePendingApproval = useAppStore((state) => state.removePendingApproval);
  const resetSessionState = useAppStore((state) => state.resetSessionState);

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", activeSessionId],
    queryFn: () => listMessages(activeSessionId as string),
    enabled: Boolean(activeSessionId),
  });

  useEffect(() => {
    const sessions = sessionsQuery.data || [];
    if (!activeSessionId && sessions.length > 0) {
      setActiveSession(sessions[0].id);
    }
  }, [sessionsQuery.data, activeSessionId, setActiveSession]);

  useEffect(() => {
    if (activeSessionId && messagesQuery.data) {
      setMessages(activeSessionId, messagesQuery.data);
    }
  }, [activeSessionId, messagesQuery.data, setMessages]);

  const sessions = sessionsQuery.data || [];
  const currentMessages = activeSessionId ? messagesBySession[activeSessionId] || [] : [];
  const liveAssistantText = activeSessionId ? liveAssistantBySession[activeSessionId] || "" : "";
  const pendingApproval = pendingApprovals[0] || null;

  async function ensureSession(): Promise<string> {
    if (activeSessionId) {
      return activeSessionId;
    }
    const created = await createSession();
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    setActiveSession(created.id);
    return created.id;
  }

  async function handleEvent(event: AgentStreamEvent): Promise<void> {
    const sid = event.sessionId;
    const payload = event.payload;

    switch (event.type) {
      case "run_started":
        setStreaming(true, event.runId);
        break;
      case "assistant_delta": {
        const text = typeof payload.text === "string" ? payload.text : "";
        appendAssistantDelta(sid, text);
        break;
      }
      case "assistant_message": {
        clearLiveAssistant(sid);
        appendMessage(sid, makeLocalMessage(sid, "assistant", "assistant_message", payload));
        break;
      }
      case "tool_use":
      case "tool_result":
      case "system_init":
      case "result":
        appendMessage(sid, makeLocalMessage(sid, "system", event.type, payload));
        break;
      case "approval_required": {
        addPendingApproval({
          approvalId: String(payload.approvalId || ""),
          runId: event.runId,
          sessionId: sid,
          toolName: String(payload.toolName || "unknown"),
          input: (payload.input as Record<string, unknown>) || {},
          expiresAt: String(payload.expiresAt || ""),
        });
        break;
      }
      case "approval_resolved": {
        const approvalId = String(payload.approvalId || "");
        removePendingApproval(approvalId);
        break;
      }
      case "run_error":
        appendMessage(sid, makeLocalMessage(sid, "system", "run_error", payload));
        break;
      case "run_completed":
        clearLiveAssistant(sid);
        setStreaming(false, null);
        break;
      default:
        break;
    }
  }

  async function handleSend(prompt: string): Promise<void> {
    const sid = await ensureSession();
    appendMessage(sid, makeLocalMessage(sid, "user", "user_prompt", { text: prompt }));
    clearLiveAssistant(sid);
    setStreaming(true, null);

    try {
      await streamRun({
        sessionId: sid,
        prompt,
        onEvent: (event) => {
          void handleEvent(event);
        },
      });
    } catch (error) {
      appendMessage(
        sid,
        makeLocalMessage(sid, "system", "run_error", {
          message: error instanceof Error ? error.message : "Streaming failed",
        }),
      );
    } finally {
      setStreaming(false, null);
      await queryClient.invalidateQueries({ queryKey: ["messages", sid] });
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    }
  }

  async function handleCreateSession(): Promise<void> {
    const created = await createSession();
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    setActiveSession(created.id);
  }

  async function handleRenameSession(sessionId: string, currentTitle: string): Promise<void> {
    const title = window.prompt("Rename session", currentTitle)?.trim();
    if (!title) {
      return;
    }
    await renameSession(sessionId, title);
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }

  async function handleDeleteSession(sessionId: string): Promise<void> {
    if (!window.confirm("Delete this session and workspace?")) {
      return;
    }
    await deleteSession(sessionId);
    resetSessionState(sessionId);
    if (activeSessionId === sessionId) {
      setActiveSession(null);
    }
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }

  return (
    <div className="min-h-full p-4 md:p-6">
      <header className="mb-5">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight">Cloud Claude Code</h1>
        <p className="text-sm text-slate-700 mt-1">Web shell for Claude Agent SDK with workspace-aware sessions.</p>
      </header>

      <div className="flex flex-col md:flex-row gap-4">
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          loading={sessionsQuery.isLoading}
          onSelect={setActiveSession}
          onCreate={() => {
            void handleCreateSession();
          }}
          onRename={(id, title) => {
            void handleRenameSession(id, title);
          }}
          onDelete={(id) => {
            void handleDeleteSession(id);
          }}
        />

        <main className="flex-1 rounded-3xl bg-white/60 border border-white/70 p-4 md:p-5 shadow-panel min-h-[72vh] flex flex-col">
          <MessageList messages={currentMessages} liveAssistantText={liveAssistantText} />
          <Composer disabled={!activeSessionId || isStreaming} onSend={handleSend} />
        </main>
      </div>

      <ApprovalModal
        pending={pendingApproval}
        onSubmit={async (approval, payload) => {
          await submitApproval(approval.runId, approval.approvalId, payload);
          removePendingApproval(approval.approvalId);
        }}
      />
    </div>
  );
}
