import { create } from "zustand";

import type { ChatMessage, PendingApproval } from "./types";

interface AppState {
  activeSessionId: string | null;
  messagesBySession: Record<string, ChatMessage[]>;
  liveAssistantBySession: Record<string, string>;
  pendingApprovals: PendingApproval[];
  isStreaming: boolean;
  currentRunId: string | null;

  setActiveSession: (sessionId: string | null) => void;
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  appendMessage: (sessionId: string, message: ChatMessage) => void;
  appendAssistantDelta: (sessionId: string, text: string) => void;
  clearLiveAssistant: (sessionId: string) => void;
  setStreaming: (isStreaming: boolean, runId: string | null) => void;
  addPendingApproval: (approval: PendingApproval) => void;
  removePendingApproval: (approvalId: string) => void;
  resetSessionState: (sessionId: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeSessionId: null,
  messagesBySession: {},
  liveAssistantBySession: {},
  pendingApprovals: [],
  isStreaming: false,
  currentRunId: null,

  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),

  setMessages: (sessionId, messages) =>
    set((state) => ({
      messagesBySession: { ...state.messagesBySession, [sessionId]: messages },
    })),

  appendMessage: (sessionId, message) =>
    set((state) => ({
      messagesBySession: {
        ...state.messagesBySession,
        [sessionId]: [...(state.messagesBySession[sessionId] || []), message],
      },
    })),

  appendAssistantDelta: (sessionId, text) =>
    set((state) => ({
      liveAssistantBySession: {
        ...state.liveAssistantBySession,
        [sessionId]: (state.liveAssistantBySession[sessionId] || "") + text,
      },
    })),

  clearLiveAssistant: (sessionId) =>
    set((state) => ({
      liveAssistantBySession: {
        ...state.liveAssistantBySession,
        [sessionId]: "",
      },
    })),

  setStreaming: (isStreaming, runId) =>
    set({
      isStreaming,
      currentRunId: runId,
    }),

  addPendingApproval: (approval) =>
    set((state) => ({
      pendingApprovals: [...state.pendingApprovals.filter((a) => a.approvalId !== approval.approvalId), approval],
    })),

  removePendingApproval: (approvalId) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter((approval) => approval.approvalId !== approvalId),
    })),

  resetSessionState: (sessionId) =>
    set((state) => {
      const { [sessionId]: _removedMessages, ...nextMessages } = state.messagesBySession;
      const { [sessionId]: _removedLive, ...nextLive } = state.liveAssistantBySession;
      return {
        messagesBySession: nextMessages,
        liveAssistantBySession: nextLive,
      };
    }),
}));
