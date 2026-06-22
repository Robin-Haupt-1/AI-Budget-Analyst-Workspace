"use client";
import { useState } from "react";
import { useBudgetChat } from "@/lib/useBudgetChat";
import { WidgetRenderer } from "./WidgetRenderer";
import { Markdown } from "./Markdown";
import { ToolCall } from "@/lib/types";


const SUGGESTIONS = [
  "Which areas are over budget this quarter?",
  "Show me the largest variances by category.",
  "Group this by department.",
  "What would happen if Marketing spend was reduced by 10%?",
  "Highlight the three biggest risks.",
];

/** " (Marketing)" / " (Marketing, Travel)" when a tool was filtered. */
function filterText(t: ToolCall): string {
  const bits = [t.args.department, t.args.category].filter(Boolean);
  return bits.length ? ` (${bits.join(", ")})` : "";
}

/** Turn a raw tool call into a plain-language line for the "how was this
 * calculated?" inspector, so the user sees the calculation, not JSON. */
function describeToolCall(t: ToolCall): string {
  switch (t.name) {
    case "list_scenarios":
      return "Listed the available budget scenarios.";
    case "load_scenario_data":
      return `Loaded the scenario's line items${filterText(t)}.`;
    case "get_variances":
      return `Computed budget-vs-actual variance and severity${filterText(t)}.`;
    case "group_by":
      return `Aggregated the line items by ${t.args.dimension ?? "department"}.`;
    case "get_top_risks":
      return `Ranked the top ${t.args.n ?? 3} over-budget items by severity.`;
    case "simulate":
      return `Simulated changing ${t.args.department}'s actual spend by ${t.args.pct_change}%.`;
    case "show_chart":
      return `Charted "${t.args.dataset}" as a ${t.args.chart_type ?? "bar"} chart.`;
    case "chart_values":
      return `Charted ${(t.args.values?.length ?? 0)} values as a ${t.args.chart_type ?? "bar"} chart.`;
    default:
      return "Computed over the budget data.";
  }
}

/** Render the underlying call as `name(param=value, …)` for the inspector. */
function formatSignature(t: ToolCall): string {
  const params = Object.entries(t.args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
  return `${t.name}(${params})`;
}

export function Chat({ scenarioId }: { scenarioId: number | null }) {
  const { messages, streaming, send, clearHistory } = useBudgetChat(scenarioId);
  const [input, setInput] = useState("");
  const [showWhy, setShowWhy] = useState<number | null>(null);

  const submit = () => { send(input); setInput(""); };

  const clear = () => {
    if (confirm("Clear this budget's chat history? This can't be undone.")) {
      setShowWhy(null);
      clearHistory();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Per-budget conversations are saved in localStorage; this clears only the
          selected budget's thread (useBudgetChat.clearHistory). */}
      {scenarioId != null && messages.length > 0 && (
        <div className="flex items-center justify-end border-b px-3 py-1.5">
          <button onClick={clear} disabled={streaming}
            className="text-xs text-gray-400 hover:text-red-600 disabled:opacity-40">
            Clear history
          </button>
        </div>
      )}
      {/* === Conversation (AI Elements: <Conversation><Message/>) === */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 && (
          <p className="text-sm text-gray-500">
            Ask about this budget scenario, or tap a suggestion below to get started.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-full rounded-lg px-3 py-2 text-sm ${
              m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-left"}`}>
              {m.role === "assistant"
                ? (m.text
                    ? <Markdown>{m.text}</Markdown>
                    : (streaming && i === messages.length - 1 ? "…" : ""))
                : m.text}
            </div>
            {m.widgets.map((w, j) => (
              <div key={j} className="mt-2 rounded-lg border bg-white p-3 text-left">
                <WidgetRenderer widget={w} />
              </div>
            ))}
            {/* Bonus: inspect which deterministic tools/calculations produced
                the answer (the "why this answer" view from the brief). */}
            {m.role === "assistant" && m.toolCalls.length > 0 && (
              <div className="mt-1 text-left">
                <button onClick={() => setShowWhy(showWhy === i ? null : i)}
                  className="text-xs text-gray-400 hover:text-gray-600">
                  {showWhy === i ? "Hide calculation details" : "How was this calculated?"}
                </button>
                {showWhy === i && (
                  <ul className="mt-1 rounded bg-gray-50 p-2 text-xs text-gray-600 list-disc pl-5 space-y-1">
                    {m.toolCalls.map((t, k) => (
                      <li key={k}>
                        <div>{describeToolCall(t)}</div>
                        <code className="block text-[11px] text-gray-400 break-all">
                          {formatSignature(t)}
                        </code>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t">
      {/* Suggestion chips stay available for the whole conversation, so a
          reviewer can keep exploring (and discover follow-ups) after turn one. */}
      {scenarioId && (
        <div className="px-3 pt-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} disabled={streaming}
              className="rounded-full border bg-gray-50 px-2.5 py-1 text-xs text-gray-600
                         hover:bg-gray-100 hover:text-gray-900 disabled:opacity-40">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* === Prompt input (AI Elements: <PromptInput>) === */}
      <div className="p-3 flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2 text-sm"
          placeholder={scenarioId ? "Ask about this budget…" : "Select a scenario first"}
          value={input} disabled={!scenarioId || streaming}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <button onClick={submit} disabled={!scenarioId || streaming || !input.trim()}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-40">
          {streaming ? "…" : "Send"}
        </button>
      </div>
      </div>
    </div>
  );
}
