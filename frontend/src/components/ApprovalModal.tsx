import { useMemo, useState } from "react";

import type { ApprovalDecisionRequest, PendingApproval } from "../types";

interface ApprovalModalProps {
  pending: PendingApproval | null;
  onSubmit: (approval: PendingApproval, payload: ApprovalDecisionRequest) => Promise<void>;
}

type QuestionOption = {
  label: string;
  description: string;
};

type AskQuestion = {
  question: string;
  header: string;
  options: QuestionOption[];
  multiSelect?: boolean;
};

export function ApprovalModal({ pending, onSubmit }: ApprovalModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});

  const questions = useMemo(() => {
    const raw = pending?.input?.questions;
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw.filter((item): item is AskQuestion => {
      if (!item || typeof item !== "object") {
        return false;
      }
      const record = item as Record<string, unknown>;
      return typeof record.question === "string" && Array.isArray(record.options);
    });
  }, [pending]);

  if (!pending) {
    return null;
  }

  const isAskUserQuestion = pending.toolName === "AskUserQuestion";

  async function submit(payload: ApprovalDecisionRequest) {
    setSubmitting(true);
    try {
      await onSubmit(pending, payload);
      setAnswers({});
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-ink/35 backdrop-blur-sm flex items-center justify-center px-4 z-50">
      <div className="w-full max-w-2xl rounded-3xl bg-white shadow-panel border border-white p-6">
        <h3 className="text-xl font-semibold">Approval Required</h3>
        <p className="mt-1 text-sm text-slate-600">
          Tool: <span className="font-mono">{pending.toolName}</span>
        </p>

        {isAskUserQuestion && questions.length > 0 ? (
          <div className="mt-4 space-y-4">
            {questions.map((question) => {
              const selected = answers[question.question] || [];
              return (
                <section key={question.question} className="rounded-xl border border-slate-200 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{question.header}</p>
                  <p className="text-sm font-medium mt-1">{question.question}</p>

                  <div className="mt-3 space-y-2">
                    {question.options.map((option) => {
                      const checked = selected.includes(option.label);
                      return (
                        <label key={option.label} className="flex gap-3 items-start rounded-lg border border-slate-200 p-2">
                          <input
                            type={question.multiSelect ? "checkbox" : "radio"}
                            checked={checked}
                            name={question.question}
                            onChange={() => {
                              setAnswers((prev) => {
                                const current = prev[question.question] || [];
                                let next: string[];
                                if (question.multiSelect) {
                                  next = checked
                                    ? current.filter((entry) => entry !== option.label)
                                    : [...current, option.label];
                                } else {
                                  next = [option.label];
                                }
                                return { ...prev, [question.question]: next };
                              });
                            }}
                          />
                          <span>
                            <span className="block text-sm font-medium">{option.label}</span>
                            <span className="block text-xs text-slate-500">{option.description}</span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        ) : (
          <pre className="mt-4 max-h-80 overflow-auto rounded-xl bg-slate-900 text-slate-100 p-3 text-xs">
            {JSON.stringify(pending.input, null, 2)}
          </pre>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={submitting}
            onClick={() =>
              void submit({
                behavior: "deny",
                message: "User denied this action from the web UI.",
              })
            }
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm"
          >
            Deny
          </button>

          <button
            type="button"
            disabled={submitting}
            onClick={() => {
              const formattedAnswers: Record<string, string> = {};
              Object.entries(answers).forEach(([question, selected]) => {
                formattedAnswers[question] = selected.join(", ");
              });

              void submit({
                behavior: "allow",
                answers: formattedAnswers,
              });
            }}
            className="rounded-xl bg-ink text-white px-4 py-2 text-sm"
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}
