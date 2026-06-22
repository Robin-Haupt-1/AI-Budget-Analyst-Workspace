"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "./api";
import { ChatMessage, SSEEvent } from "./types";

/**
 * Minimal chat hook that speaks OUR explicit Django SSE protocol
 * (backend/assistant/events.py) rather than coupling to a vendor wire format.
 * It streams text deltas into the current assistant message and collects
 * widget + tool_call events. AI Elements is used purely for presentation
 * (see components/Chat.tsx). This keeps the backend boundary clean and typed —
 * a deliberate choice documented in the README.
 *
 * Conversations are persisted per-budget in localStorage so a reviewer can
 * reload the page or switch between scenarios without losing context. Each
 * budget keeps its own history; selecting a budget always loads that budget's
 * conversation, and `clearHistory` wipes just the selected budget's thread.
 */
const storageKey = (scenarioId: number) => `budget-chat-history:${scenarioId}`;

function loadHistory(scenarioId: number | null): ChatMessage[] {
  if (scenarioId == null || typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey(scenarioId));
    return raw ? (JSON.parse(raw) as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

export function useBudgetChat(scenarioId: number | null) {
  // Tag the messages with the scenario they belong to so persistence and
  // scenario-switching can never write one budget's history under another's key
  // (state updates lag a render behind a scenarioId change otherwise).
  const [state, setState] = useState<{ sid: number | null; messages: ChatMessage[] }>(
    () => ({ sid: scenarioId, messages: loadHistory(scenarioId) }),
  );
  const [streaming, setStreaming] = useState(false);
  const messages = state.messages;
  // Tracks the in-flight stream so switching budgets can cancel it.
  const abortRef = useRef<AbortController | null>(null);

  // Whenever the selected budget changes, cancel any in-flight stream (its
  // events belong to the previous budget) and load the new budget's history.
  useEffect(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setState({ sid: scenarioId, messages: loadHistory(scenarioId) });
  }, [scenarioId]);

  // Persist on turn completion rather than on every streamed token: `streaming`
  // flips false when a turn finishes, on clear, and on budget switch — each a
  // point where stored history should match what's on screen. sid + messages
  // always move together, so this writes the right history under the right key.
  useEffect(() => {
    if (streaming || state.sid == null || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(storageKey(state.sid), JSON.stringify(state.messages));
    } catch {
      /* ignore quota / serialization errors — persistence is best-effort */
    }
  }, [state, streaming]);

  const setMessages = useCallback(
    (fn: (m: ChatMessage[]) => ChatMessage[]) =>
      setState((s) => ({ ...s, messages: fn(s.messages) })),
    [],
  );

  const clearHistory = useCallback(() => {
    setMessages(() => []);
  }, [setMessages]);

  const send = useCallback(async (text: string) => {
    if (!scenarioId || !text.trim()) return;
    // Include each assistant turn's tool calls so the agent knows which
    // computations the prior turn ran — context that "group this by …" /
    // "show only high risk" follow-ups depend on. The backend folds these into
    // the message content (numbers are still recomputed by re-running tools).
    const history = messages.map((m) => ({
      role: m.role,
      content: m.text,
      tool_calls: m.toolCalls,
    }));

    setMessages((m) => [
      ...m,
      { role: "user", text, widgets: [], toolCalls: [] },
      { role: "assistant", text: "", widgets: [], toolCalls: [] },
    ]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    // Apply a stream event to the open assistant turn — but only if it still
    // belongs to this budget and the slot exists. Switching budgets mid-stream
    // swaps `messages` out from under us, so guard before touching the last one.
    const patchAssistant = (fn: (a: ChatMessage) => ChatMessage) =>
      setState((s) => {
        if (s.sid !== scenarioId || s.messages.length === 0) return s;
        const last = s.messages[s.messages.length - 1];
        if (last.role !== "assistant") return s;
        const copy = [...s.messages];
        copy[copy.length - 1] = fn(last);
        return { ...s, messages: copy };
      });

    try {
      const res = await fetch(`${api.base}/api/assistant/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: scenarioId, message: text, history }),
        signal: controller.signal,
      });
      if (!res.body) throw new Error("no response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const frames = buf.split("\n\n");
        buf = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const ev = JSON.parse(line.slice(5).trim()) as SSEEvent;
          if (ev.type === "text_delta")
            patchAssistant((a) => ({ ...a, text: a.text + ev.content }));
          else if (ev.type === "widget")
            patchAssistant((a) => ({ ...a, widgets: [...a.widgets, ev.widget] }));
          else if (ev.type === "tool_call")
            patchAssistant((a) => ({
              ...a, toolCalls: [...a.toolCalls, { name: ev.name, args: ev.args }],
            }));
          else if (ev.type === "error")
            patchAssistant((a) => ({ ...a, text: a.text + `\n[error: ${ev.message}]` }));
        }
      }
    } catch (e: any) {
      // The stream was cancelled because the user switched budgets — not an error.
      if (e?.name === "AbortError") return;
      patchAssistant((a) => ({ ...a, text: a.text + `\n[error: ${e.message}]` }));
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setStreaming(false);
    }
  }, [scenarioId, messages, setMessages]);

  return { messages, streaming, send, clearHistory };
}
