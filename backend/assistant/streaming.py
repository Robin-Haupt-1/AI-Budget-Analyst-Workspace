"""
Bridge: run the agent in streaming mode and translate its events into our SSE
protocol (events.py). This is the clean backend boundary the brief asks for.

Flow:
  user message --> Runner.run_streamed(agent, ..., context=BudgetContext) -->
     - text token deltas        -> {"type":"text_delta"}
     - tool call started        -> {"type":"tool_call"}        (for "why this answer")
     - tool output produced     -> {"type":"widget"}           (the structured result)
  end -> {"type":"done"}

"""
from __future__ import annotations

import json
from typing import AsyncIterator

from agents import Runner

from . import events
from .agent import build_agent
from .tools import BudgetContext


def _extract_widget(raw_output) -> dict | None:
    """Tool outputs are {'widget_kind': ..., 'data': ...}. Normalise to a widget."""
    data = raw_output
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    if isinstance(data, dict) and "widget_kind" in data:
        return events.widget(data["widget_kind"], data.get("data"))
    return None


def _format_tool_calls(tool_calls) -> str:
    """Render an assistant turn's tool calls as a compact note, e.g.
    'group_by(dimension=department), get_top_risks(n=3)'. Empty/malformed
    entries are skipped; returns "" if there's nothing to show."""
    parts = []
    for t in tool_calls or []:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        args = t.get("args") or {}
        arg_str = (
            ", ".join(f"{k}={v}" for k, v in args.items())
            if isinstance(args, dict) else ""
        )
        parts.append(f"{t['name']}({arg_str})")
    return ", ".join(parts)


def build_input(message: str, history: list | None = None) -> list[dict]:
    """Fold prior turns + the new message into the agent's input list.

    Gives the agent conversational context so follow-ups like "group this by
    department" or "show only the high-risk ones" — which only make sense
    relative to the previous turn — work. Each history item is
    {"role": "user"|"assistant", "content": str, "tool_calls"?: [...]}.
    For assistant turns, the tool calls that produced the answer are appended to
    the content so the agent knows what was computed last turn. We keep only
    narration text + which tools ran; the numbers are always recomputed by
    re-running tools against the live data, never trusted from history.
    """
    items: list[dict] = []
    for h in history or []:
        if not isinstance(h, dict) or h.get("role") not in ("user", "assistant"):
            continue
        text = h.get("content") or ""
        if h["role"] == "assistant":
            calls = _format_tool_calls(h.get("tool_calls"))
            if calls:
                note = f"[Computed via tools: {calls}]"
                text = f"{text}\n{note}" if text else note
        if not text:
            continue
        items.append({"role": h["role"], "content": text})
    items.append({"role": "user", "content": message})
    return items


async def run_chat_stream(scenario_id: int, message: str,
                          history: list | None = None) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for one user turn."""
    agent = build_agent()
    ctx = BudgetContext(scenario_id=scenario_id)
    input_list = build_input(message, history)

    try:
        result = Runner.run_streamed(agent, input=input_list, context=ctx)
        async for ev in result.stream_events():
            # 1) token deltas from the model's narration.
            # The raw response stream carries BOTH visible text deltas AND
            # function-call ARGUMENT deltas (both expose a `.delta` string).
            # Only the text-output deltas are narration; forwarding the
            # argument deltas would leak raw JSON like {"dimension":"..."} into
            # the chat bubble. Gate on the event subtype to keep them separate.
            if ev.type == "raw_response_event":
                if getattr(ev.data, "type", "") == "response.output_text.delta":
                    delta = getattr(ev.data, "delta", None)
                    if isinstance(delta, str) and delta:
                        yield events.sse(events.text_delta(delta))

            # 2) tool calls + tool outputs
            elif ev.type == "run_item_stream_event":
                item = ev.item
                item_type = getattr(item, "type", "")
                if item_type == "tool_call_item":
                    name = getattr(getattr(item, "raw_item", None), "name", "tool")
                    args = getattr(getattr(item, "raw_item", None), "arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"raw": args}
                    yield events.sse(events.tool_call(name, args))
                elif item_type == "tool_call_output_item":
                    w = _extract_widget(getattr(item, "output", None))
                    if w:
                        yield events.sse(w)

        yield events.sse(events.DONE)
    except Exception as exc:  # surface errors to the UI instead of hanging
        yield events.sse(events.error(str(exc)))
        yield events.sse(events.DONE)
