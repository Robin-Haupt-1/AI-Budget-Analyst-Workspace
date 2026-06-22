"""
SSE event protocol — the clean boundary between the Python agent and the React UI.

The frontend's custom transport (frontend/lib/transport.ts) parses exactly these
shapes. Keep this file and that file in sync.

Event shapes (one JSON object per SSE `data:` line):
  {"type": "text_delta", "content": "..."}          # narration token(s)
  {"type": "widget", "widget": {"kind": "...", "data": {...}}}  # structured result
  {"type": "tool_call", "name": "...", "args": {...}}  # for the "why this answer" view
  {"type": "done"}
  {"type": "error", "message": "..."}

Widget kinds (all generic + reusable): "data_table" | "chart" | "stat_card"
  - data_table: {name, title, columns: [...], rows: [...]}   (any data/calc tool)
  - chart:      {chart_type: bar|line|pie, x, y, title, rows} (show_chart/chart_values)
  - stat_card:  {title, items: [{label, value, tone?}]}       (e.g. the what-if)
"""
import json


def sse(event: dict) -> str:
    """Format a dict as one SSE message."""
    return f"data: {json.dumps(event)}\n\n"


def text_delta(content: str) -> dict:
    return {"type": "text_delta", "content": content}


def widget(kind: str, data) -> dict:
    return {"type": "widget", "widget": {"kind": kind, "data": data}}


def tool_call(name: str, args: dict) -> dict:
    return {"type": "tool_call", "name": name, "args": args}


DONE = {"type": "done"}


def error(message: str) -> dict:
    return {"type": "error", "message": message}
