import type { ChatResponse, SessionDetail, SessionSummary, StreamDoneEvent } from "../types/chat";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";
const WS_BASE = API_BASE.replace(/^http/, "ws");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const apiClient = {
  listSessions: () => request<SessionSummary[]>("/sessions"),
  createSession: (title = "New Session") =>
    request<SessionSummary>("/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  getSession: (sessionId: string) => request<SessionDetail>(`/sessions/${sessionId}`),
  sendMessage: (sessionId: string, content: string) =>
    request<ChatResponse>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  streamMessage: (
    sessionId: string,
    content: string,
    handlers: {
      onToken: (token: string) => void;
      onInit: (slashCommands: string[]) => void;
    },
  ) =>
    new Promise<StreamDoneEvent>((resolve, reject) => {
      const ws = new WebSocket(`${WS_BASE}/sessions/${sessionId}/ws`);
      let settled = false;

      ws.onopen = () => {
        ws.send(JSON.stringify({ content }));
      };

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data) as Record<string, unknown>;
        const type = String(payload.type ?? "");

        if (type === "token") {
          handlers.onToken(String(payload.text ?? ""));
          return;
        }

        if (type === "init") {
          handlers.onInit(Array.isArray(payload.slash_commands) ? (payload.slash_commands as string[]) : []);
          return;
        }

        if (type === "error") {
          settled = true;
          ws.close();
          reject(new Error(String(payload.error ?? "WebSocket error")));
          return;
        }

        if (type === "done") {
          settled = true;
          ws.close();
          resolve(payload as unknown as StreamDoneEvent);
        }
      };

      ws.onerror = () => {
        if (settled) {
          return;
        }
        settled = true;
        reject(new Error("WebSocket connection failed"));
      };

      ws.onclose = () => {
        if (!settled) {
          settled = true;
          reject(new Error("WebSocket closed unexpectedly"));
        }
      };
    }),
};
