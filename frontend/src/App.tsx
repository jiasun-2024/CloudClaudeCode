import { useEffect, useMemo, useState } from "react";

import { apiClient } from "./api/client";
import { ChatWindow } from "./components/ChatWindow";
import { SessionSidebar } from "./components/SessionSidebar";
import type { Message, SessionDetail, SessionSummary } from "./types/chat";

export default function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionDetail, setActiveSessionDetail] = useState<SessionDetail | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void initialize();
  }, []);

  async function initialize() {
    try {
      const existing = await apiClient.listSessions();
      setSessions(existing);

      if (existing.length) {
        await selectSession(existing[0].session_id);
        return;
      }

      await createSession();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function createSession() {
    setError(null);
    const created = await apiClient.createSession();
    setSessions((prev) => [created, ...prev.filter((item) => item.session_id !== created.session_id)]);
    await selectSession(created.session_id);
  }

  async function selectSession(sessionId: string) {
    setError(null);
    const detail = await apiClient.getSession(sessionId);
    setActiveSessionId(sessionId);
    setActiveSessionDetail(detail);
  }

  async function sendMessage(content: string) {
    if (!activeSessionId || !activeSessionDetail) {
      return;
    }

    setSending(true);
    setError(null);

    const startedAt = new Date().toISOString();
    const tempAssistantAt = new Date(Date.now() + 1).toISOString();
    const optimisticUser: Message = { role: "user", content, created_at: startedAt };
    const optimisticAssistant: Message = { role: "assistant", content: "", created_at: tempAssistantAt };

    setActiveSessionDetail((prev) => {
      if (!prev) {
        return prev;
      }
      return {
        ...prev,
        messages: [...prev.messages, optimisticUser, optimisticAssistant],
      };
    });

    try {
      let streamed = "";
      const done = await apiClient.streamMessage(activeSessionId, content, {
        onToken: (token) => {
          streamed += token;
          setActiveSessionDetail((prev) => {
            if (!prev || !prev.messages.length) {
              return prev;
            }
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last.role !== "assistant" || last.created_at !== tempAssistantAt) {
              return prev;
            }
            updated[updated.length - 1] = { ...last, content: streamed };
            return { ...prev, messages: updated };
          });
        },
        onInit: (slashCommands) => {
          setActiveSessionDetail((prev) => (prev ? { ...prev, slash_commands: slashCommands } : prev));
        },
      });

      setActiveSessionDetail((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          messages: done.messages,
          slash_commands: done.slash_commands,
        };
      });

      const latestSessions = await apiClient.listSessions();
      setSessions(latestSessions);
    } catch (err) {
      setError((err as Error).message);
      const recovered = await apiClient.getSession(activeSessionId);
      setActiveSessionDetail(recovered);
    } finally {
      setSending(false);
    }
  }

  const messages = useMemo(() => activeSessionDetail?.messages ?? [], [activeSessionDetail]);
  const slashCommands = useMemo(
    () => activeSessionDetail?.slash_commands ?? [],
    [activeSessionDetail],
  );

  return (
    <main className="app-shell">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onCreateSession={() => void createSession()}
        onSelectSession={(sessionId) => void selectSession(sessionId)}
      />

      <div className="chat-panel">
        {error ? <p className="error">{error}</p> : null}
        <ChatWindow
          messages={messages}
          slashCommands={slashCommands}
          sending={sending}
          onSend={sendMessage}
        />
      </div>
    </main>
  );
}
