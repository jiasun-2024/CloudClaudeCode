import type { SessionSummary } from "../types/chat";

type Props = {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
};

export function SessionSidebar({
  sessions,
  activeSessionId,
  onCreateSession,
  onSelectSession,
}: Props) {
  return (
    <aside className="sidebar">
      <header className="sidebar-header">
        <h1>Cloud Claude Code</h1>
        <button onClick={onCreateSession}>New</button>
      </header>

      <ul className="session-list">
        {sessions.map((session) => (
          <li key={session.session_id}>
            <button
              className={activeSessionId === session.session_id ? "active" : ""}
              onClick={() => onSelectSession(session.session_id)}
            >
              <span>{session.title}</span>
              <small>{new Date(session.last_active_at).toLocaleString()}</small>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
