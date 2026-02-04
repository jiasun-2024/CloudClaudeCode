import { FormEvent, useMemo, useState } from "react";

import type { Message } from "../types/chat";

type Props = {
  messages: Message[];
  slashCommands: string[];
  sending: boolean;
  onSend: (content: string) => Promise<void>;
};

export function ChatWindow({ messages, slashCommands, sending, onSend }: Props) {
  const [input, setInput] = useState("");

  const placeholder = useMemo(() => {
    if (!slashCommands.length) {
      return "Ask Claude to code, refactor, or run a slash command...";
    }
    return `Try commands: ${slashCommands.slice(0, 4).join(", ")} ...`;
  }, [slashCommands]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content || sending) {
      return;
    }

    setInput("");
    await onSend(content);
  }

  return (
    <section className="chat-window">
      <div className="messages">
        {messages.map((message, index) => (
          <article key={`${message.created_at}-${index}`} className={`message ${message.role}`}>
            <p>{message.content}</p>
            <time>{new Date(message.created_at).toLocaleTimeString()}</time>
          </article>
        ))}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={placeholder}
          disabled={sending}
        />
        <button type="submit" disabled={sending || !input.trim()}>
          {sending ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
