export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  meta?: Record<string, string>;
}

export interface SessionSummary {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface MessageListResponse {
  session_id: string;
  messages: ChatMessage[];
}

export interface SessionCreateResponse {
  id: string;
  title: string;
}
