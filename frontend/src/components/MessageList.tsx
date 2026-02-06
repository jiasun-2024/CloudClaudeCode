import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
  liveAssistantText: string;
}

function messageText(message: ChatMessage): string {
  const raw = message.content_json;
  if (typeof raw.text === "string") {
    return raw.text;
  }
  if (typeof raw.message === "string") {
    return raw.message;
  }
  return JSON.stringify(raw, null, 2);
}

export function MessageList({ messages, liveAssistantText }: MessageListProps) {
  return (
    <div className="flex-1 overflow-auto pr-1 space-y-4">
      {messages.map((message) => {
        const isUser = message.role === "user";
        const bubbleClass = isUser
          ? "bg-ink text-white ml-auto"
          : message.role === "assistant"
            ? "bg-white border border-slate-200 text-slate-900"
            : "bg-slate-100 border border-slate-200 text-slate-700";

        return (
          <article key={message.id} className={`max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-wrap ${bubbleClass}`}>
            <p className="text-[11px] uppercase tracking-wide opacity-70 mb-1">{message.role}</p>
            <p className="text-sm leading-relaxed">{messageText(message)}</p>
          </article>
        );
      })}

      {liveAssistantText && (
        <article className="max-w-[85%] rounded-2xl px-4 py-3 bg-white border border-tide/40 text-slate-900 whitespace-pre-wrap animate-pulse">
          <p className="text-[11px] uppercase tracking-wide opacity-70 mb-1">assistant</p>
          <p className="text-sm leading-relaxed">{liveAssistantText}</p>
        </article>
      )}
    </div>
  );
}
