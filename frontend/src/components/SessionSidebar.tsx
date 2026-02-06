import type { SessionSummary } from "../types";

interface SessionSidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, currentTitle: string) => void;
  onDelete: (id: string) => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  loading,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: SessionSidebarProps) {
  return (
    <aside className="w-full md:w-80 rounded-3xl bg-white/70 backdrop-blur-lg border border-white/70 shadow-panel p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold tracking-tight">Sessions</h2>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-xl bg-ink text-white px-3 py-2 text-sm font-medium hover:bg-slate-800"
        >
          New
        </button>
      </div>

      {loading && <p className="text-sm text-slate-600">Loading sessions...</p>}

      {!loading && sessions.length === 0 && (
        <p className="text-sm text-slate-600">No sessions yet. Create your first one.</p>
      )}

      <ul className="space-y-2 max-h-[70vh] overflow-auto pr-1">
        {sessions.map((session) => {
          const active = session.id === activeSessionId;
          return (
            <li key={session.id}>
              <button
                type="button"
                onClick={() => onSelect(session.id)}
                className={`w-full text-left rounded-2xl border p-3 transition ${
                  active
                    ? "border-ink bg-ink text-white"
                    : "border-slate-200 bg-white/80 text-slate-800 hover:border-tide"
                }`}
              >
                <div className="font-medium line-clamp-1">{session.title}</div>
                <div className={`text-xs mt-1 ${active ? "text-slate-200" : "text-slate-500"}`}>
                  {session.status}
                </div>
                <div className="mt-3 flex gap-2">
                  <span
                    onClick={(event) => {
                      event.stopPropagation();
                      onRename(session.id, session.title);
                    }}
                    className="inline-flex rounded-lg border border-current/30 px-2 py-1 text-xs cursor-pointer"
                  >
                    Rename
                  </span>
                  <span
                    onClick={(event) => {
                      event.stopPropagation();
                      onDelete(session.id);
                    }}
                    className="inline-flex rounded-lg border border-current/30 px-2 py-1 text-xs cursor-pointer"
                  >
                    Delete
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
