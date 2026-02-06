export type SessionStatus = "active" | "deleting_failed" | string;

export interface SessionSummary {
  id: string;
  title: string;
  workspace_path: string;
  sdk_session_id: string | null;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionResponse {
  id: string;
  title: string;
  workspace_path: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: string;
  kind: string;
  content_json: Record<string, unknown>;
  created_at: string;
}

export interface AgentStreamEvent {
  type: string;
  runId: string;
  sessionId: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface ApprovalDecisionRequest {
  behavior: "allow" | "deny";
  updated_input?: Record<string, unknown>;
  message?: string;
  answers?: Record<string, unknown>;
}

export interface PendingApproval {
  approvalId: string;
  runId: string;
  sessionId: string;
  toolName: string;
  input: Record<string, unknown>;
  expiresAt: string;
}
