import { useState } from "react";

interface ComposerProps {
  disabled: boolean;
  onSend: (prompt: string) => Promise<void>;
}

export function Composer({ disabled, onSend }: ComposerProps) {
  const [input, setInput] = useState("");

  const submit = async () => {
    const prompt = input.trim();
    if (!prompt || disabled) {
      return;
    }
    setInput("");
    await onSend(prompt);
  };

  return (
    <div className="mt-4 rounded-2xl bg-white/80 border border-white p-3 shadow-panel">
      <textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Ask Claude to inspect code, edit files, or run commands..."
        rows={3}
        className="w-full resize-none bg-transparent outline-none text-sm leading-relaxed"
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            void submit();
          }
        }}
      />
      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-slate-500">Press Ctrl/Cmd + Enter to send</p>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={disabled}
          className="rounded-xl bg-amber px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
