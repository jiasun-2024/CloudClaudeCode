import type {
  MessageListResponse,
  SessionCreateResponse,
  SessionSummary,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function getSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE}/api/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to load sessions: ${response.status}`);
  }
  return response.json();
}

export async function createSession(title?: string): Promise<SessionCreateResponse> {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.status}`);
  }
  return response.json();
}

export async function getSessionMessages(sessionId: string): Promise<MessageListResponse> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  if (!response.ok) {
    throw new Error(`Failed to load messages: ${response.status}`);
  }
  return response.json();
}

export async function streamMessage(
  sessionId: string,
  content: string,
  onEvent: (event: string, payload: unknown) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Stream request failed: ${response.status} ${text}`);
  }

  if (!response.body) {
    throw new Error("Stream body is empty");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const lines = part.split("\n");
      let eventName = "message";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          data += line.slice(5).trim();
        }
      }

      if (data) {
        try {
          onEvent(eventName, JSON.parse(data));
        } catch {
          onEvent(eventName, data);
        }
      }
    }
  }
}
