import {
  type AgentStreamEvent,
  type ApprovalDecisionRequest,
  type ChatMessage,
  type CreateSessionResponse,
  type SessionSummary,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  return readJson<SessionSummary[]>(response);
}

export async function createSession(title?: string): Promise<CreateSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || null }),
  });
  return readJson<CreateSessionResponse>(response);
}

export async function renameSession(sessionId: string, title: string): Promise<SessionSummary> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return readJson<SessionSummary>(response);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { method: "DELETE" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
}

export async function listMessages(sessionId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
  return readJson<ChatMessage[]>(response);
}

export async function submitApproval(
  runId: string,
  approvalId: string,
  payload: ApprovalDecisionRequest,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/approvals/${approvalId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
}

interface StreamRunParams {
  sessionId: string;
  prompt: string;
  model?: string;
  onEvent: (event: AgentStreamEvent) => void;
}

export async function streamRun({ sessionId, prompt, model, onEvent }: StreamRunParams): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/runs/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, model: model || null }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming response body is empty");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      if (buffer.trim()) {
        parseSseBlock(buffer, onEvent);
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");

    while (boundary !== -1) {
      const rawBlock = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      parseSseBlock(rawBlock, onEvent);
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseSseBlock(block: string, onEvent: (event: AgentStreamEvent) => void): void {
  if (!block.trim()) {
    return;
  }

  const lines = block.split("\n");
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return;
  }

  try {
    const parsed = JSON.parse(dataLines.join("\n")) as AgentStreamEvent;
    onEvent(parsed);
  } catch {
    // Ignore malformed chunks and continue stream consumption.
  }
}
