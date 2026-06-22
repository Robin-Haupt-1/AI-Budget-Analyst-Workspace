"""Tests for the SSE streaming bridge (`run_chat_stream`).

This pins the most version-sensitive seam in the app: the code in `streaming.py`
that parses the OpenAI Agents SDK's streamed events and re-emits them in OUR SSE
protocol (`events.py`). We mock the SDK's `Runner` so the bridge can be exercised
with no live model, no API key, and no database — the test feeds hand-built SDK
events and asserts the exact SSE frames that come out.

It also guards two easy-to-regress behaviours:
  * text narration is forwarded, but function-call ARGUMENT deltas are NOT
    (otherwise raw JSON like {"department":...} would leak into the chat bubble);
  * a failure mid-run is surfaced as an `error` event and the stream still closes
    with `done`.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from assistant import streaming


class FakeRunResult:
    """Stand-in for the object Runner.run_streamed(...) returns: it just needs an
    async `stream_events()` that yields our pre-built fake SDK events."""

    def __init__(self, events):
        self._events = events

    async def stream_events(self):
        for ev in self._events:
            yield ev


# --- fake SDK event builders (mirror the attributes streaming.py reads) ------
def _text_delta(text):
    """A model narration token -> should become a text_delta SSE event."""
    return SimpleNamespace(
        type="raw_response_event",
        data=SimpleNamespace(type="response.output_text.delta", delta=text),
    )


def _args_delta(fragment):
    """A function-call ARGUMENT token -> must be ignored (not narration)."""
    return SimpleNamespace(
        type="raw_response_event",
        data=SimpleNamespace(type="response.function_call_arguments.delta", delta=fragment),
    )


def _tool_call(name, arguments):
    return SimpleNamespace(
        type="run_item_stream_event",
        item=SimpleNamespace(
            type="tool_call_item",
            raw_item=SimpleNamespace(name=name, arguments=arguments),
        ),
    )


def _tool_output(output):
    return SimpleNamespace(
        type="run_item_stream_event",
        item=SimpleNamespace(type="tool_call_output_item", output=output),
    )


def _drain(message, events=None, run_streamed_side_effect=None):
    """Run run_chat_stream with a mocked Runner/agent and return parsed events."""
    async def drive():
        frames = []
        async for frame in streaming.run_chat_stream(1, message):
            frames.append(frame)
        return frames

    with patch.object(streaming, "build_agent", return_value=object()), \
         patch.object(streaming, "Runner") as mock_runner:
        if run_streamed_side_effect is not None:
            mock_runner.run_streamed.side_effect = run_streamed_side_effect
        else:
            mock_runner.run_streamed.return_value = FakeRunResult(events or [])
        frames = asyncio.run(drive())

    parsed = []
    for f in frames:
        # events.sse() formats exactly as "data: {json}\n\n".
        assert f.startswith("data: ") and f.endswith("\n\n"), f
        parsed.append(json.loads(f[len("data: "):].strip()))
    return parsed


class RunChatStreamTests(SimpleTestCase):
    def test_translates_sdk_events_into_sse_protocol(self):
        events = [
            _text_delta("Marketing "),
            _args_delta('{"department":"Marketing"}'),     # must NOT leak into chat
            _tool_call("get_variances", '{"department": "Marketing"}'),
            _tool_output({"widget_kind": "data_table",
                          "data": {"name": "variances", "rows": []}}),
            _text_delta("is the biggest overspend."),
        ]
        out = _drain("which areas are over budget?", events)

        # Stream closes with exactly one done.
        self.assertEqual(out[-1]["type"], "done")
        self.assertEqual([e["type"] for e in out].count("done"), 1)

        # Narration = only the two text deltas; the function-args delta is gated out.
        text = "".join(e["content"] for e in out if e["type"] == "text_delta")
        self.assertEqual(text, "Marketing is the biggest overspend.")
        self.assertNotIn("department", text)

        # Tool call surfaced (for "why this answer"), with args JSON-decoded.
        calls = [e for e in out if e["type"] == "tool_call"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "get_variances")
        self.assertEqual(calls[0]["args"], {"department": "Marketing"})

        # Tool output became a widget event of the right kind.
        widgets = [e for e in out if e["type"] == "widget"]
        self.assertEqual(len(widgets), 1)
        self.assertEqual(widgets[0]["widget"]["kind"], "data_table")

    def test_a_failure_is_surfaced_as_error_then_done(self):
        out = _drain("boom", run_streamed_side_effect=RuntimeError("kaboom"))
        self.assertEqual(out[0]["type"], "error")
        self.assertIn("kaboom", out[0]["message"])
        self.assertEqual(out[-1]["type"], "done")
