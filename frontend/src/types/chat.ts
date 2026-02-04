export type Message = {
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type SessionSummary = {
  session_id: string;
  title: string;
  workspace_path: string;
  created_at: string;
  last_active_at: string;
};

export type SessionDetail = SessionSummary & {
  slash_commands: string[];
  messages: Message[];
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  messages: Message[];
  events: Array<Record<string, unknown>>;
};

export type StreamDoneEvent = {
  type: "done";
  reply: string;
  messages: Message[];
  slash_commands: string[];
};
