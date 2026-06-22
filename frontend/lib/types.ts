// Mirror of the backend SSE protocol (backend/assistant/events.py). Keep in sync.
// All generic: data_table = any rows; chart = any series; stat_card = label/value stats.
export type WidgetKind = "data_table" | "chart" | "stat_card";

export interface Widget { kind: WidgetKind; data: any; }
export interface ToolCall { name: string; args: Record<string, any>; }

export type SSEEvent =
  | { type: "text_delta"; content: string }
  | { type: "widget"; widget: Widget }
  | { type: "tool_call"; name: string; args: Record<string, any> }
  | { type: "done" }
  | { type: "error"; message: string };

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  widgets: Widget[];
  toolCalls: ToolCall[];   // powers the optional "why this answer" view
}

export interface Scenario {
  id: number; name: string; period: string; description: string;
  line_items: LineItem[];
}
export interface LineItem {
  id: number; scenario: number; department: string; category: string;
  budget_amount: string; actual_amount: string; notes: string;
}
