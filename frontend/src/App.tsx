import { FormEvent, useEffect, useMemo, useState } from "react";
import "./App.css";
import { createSession, getSessionMessages, getSessions, streamMessage } from "./api";
import type { ChatMessage, SessionSummary } from "./types";

function formatTime(isoTime: string): string {
  const date = new Date(isoTime);
  return date.toLocaleString();
}

function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streamingAssistant, setStreamingAssistant] = useState("");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  async function refreshSessions(): Promise<SessionSummary[]> {
    const data = await getSessions();
    setSessions(data);
    return data;
  }

  async function loadMessages(sessionId: string): Promise<void> {
    const data = await getSessionMessages(sessionId);
    setMessages(data.messages);
  }

  async function ensureSession(): Promise<void> {
    const list = await refreshSessions();
    if (list.length > 0) {
      setActiveSessionId((current) => current ?? list[0].id);
      return;
    }

    const created = await createSession("Main Session");
    await refreshSessions();
    setActiveSessionId(created.id);
  }

  useEffect(() => {
    ensureSession().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : String(err));
    });
  }, []);

  useEffect(() => {
    if (!activeSessionId) {
      return;
    }
    loadMessages(activeSessionId).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : String(err));
    });
  }, [activeSessionId]);

  async function handleCreateSession(): Promise<void> {
    try {
      const created = await createSession(`Session ${sessions.length + 1}`);
      await refreshSessions();
      setActiveSessionId(created.id);
      setMessages([]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!activeSessionId || busy) {
      return;
    }

    const content = input.trim();
    if (!content) {
      return;
    }

    const optimisticUserMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setInput("");
    setBusy(true);
    setError(null);
    setStatus("Thinking...");
    setStreamingAssistant("");
    setMessages((prev) => [...prev, optimisticUserMessage]);

    try {
      await streamMessage(activeSessionId, content, (eventName, payload) => {
        if (eventName === "assistant_delta") {
          if (typeof payload === "object" && payload && "text" in payload) {
            setStreamingAssistant((prev) => prev + String(payload.text ?? ""));
          }
          return;
        }

        if (eventName === "assistant_message") {
          if (
            typeof payload === "object" &&
            payload &&
            "content" in payload &&
            typeof payload.content === "string"
          ) {
            setMessages((prev) => [...prev, payload as ChatMessage]);
            setStreamingAssistant("");
          }
          return;
        }

        if (eventName === "tool_use") {
          if (typeof payload === "object" && payload && "tool_name" in payload) {
            setStatus(`Using tool: ${String(payload.tool_name)}`);
          }
          return;
        }

        if (eventName === "result") {
          setStatus("Completed");
          return;
        }

        if (eventName === "error") {
          if (typeof payload === "object" && payload && "message" in payload) {
            setError(String(payload.message));
          }
        }
      });

      await refreshSessions();
      await loadMessages(activeSessionId);
      setStatus("Ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Failed");
    } finally {
      setBusy(false);
      setStreamingAssistant("");
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Claude Code Web</h1>
          <button onClick={handleCreateSession} type="button">
            New
          </button>
        </div>

        <div className="session-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              className={session.id === activeSessionId ? "session active" : "session"}
              onClick={() => setActiveSessionId(session.id)}
              type="button"
            >
              <span>{session.title}</span>
              <small>{session.message_count} messages</small>
            </button>
          ))}
        </div>
      </aside>

      <main className="chat-area">
        <header className="chat-header">
          <div>
            <h2>{activeSession?.title ?? "No Session"}</h2>
            <p>{status}</p>
          </div>
        </header>

        <section className="messages">
          {messages.map((message) => (
            <article className={`bubble ${message.role}`} key={message.id}>
              <header>
                <strong>{message.role}</strong>
                <time>{formatTime(message.created_at)}</time>
              </header>
              <p>{message.content}</p>
            </article>
          ))}

          {streamingAssistant && (
            <article className="bubble assistant">
              <header>
                <strong>assistant</strong>
                <time>streaming...</time>
              </header>
              <p>{streamingAssistant}</p>
            </article>
          )}
        </section>

        {error && <p className="error">{error}</p>}

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            disabled={!activeSessionId || busy}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type your message..."
            rows={4}
            value={input}
          />
          <button disabled={!activeSessionId || busy || input.trim() === ""} type="submit">
            {busy ? "Sending..." : "Send"}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
