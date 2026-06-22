"""Tests for the SSE bridge's pure helpers.

`build_input` carries the multi-turn context the agent needs for follow-up
questions, so its filtering/ordering is worth pinning down without needing a
live model. No database is touched, so this is a SimpleTestCase.
"""
from django.test import SimpleTestCase

from assistant.streaming import build_input


class BuildInputTests(SimpleTestCase):
    def test_appends_current_message_last(self):
        out = build_input("Group this by department.")
        self.assertEqual(out, [{"role": "user", "content": "Group this by department."}])

    def test_preserves_prior_turns_in_order(self):
        history = [
            {"role": "user", "content": "Which areas are over budget?"},
            {"role": "assistant", "content": "Marketing and Sales are over."},
        ]
        out = build_input("Now show only high risk.", history)
        self.assertEqual([m["role"] for m in out], ["user", "assistant", "user"])
        self.assertEqual(out[-1]["content"], "Now show only high risk.")
        self.assertEqual(out[0]["content"], "Which areas are over budget?")

    def test_drops_empty_and_malformed_items(self):
        history = [
            {"role": "user", "content": ""},          # empty -> dropped
            {"role": "system", "content": "ignore"},  # unsupported role -> dropped
            {"role": "assistant"},                     # no content/tools -> dropped
            "not a dict",                              # malformed -> dropped
        ]
        out = build_input("Hello", history)
        self.assertEqual(out, [{"role": "user", "content": "Hello"}])

    def test_assistant_tool_calls_are_folded_into_content(self):
        history = [
            {"role": "user", "content": "Group this by department."},
            {
                "role": "assistant",
                "content": "Marketing is the biggest overspend.",
                "tool_calls": [{"name": "group_by", "args": {"dimension": "department"}}],
            },
        ]
        out = build_input("Now show only high risk.", history)
        assistant = out[1]
        self.assertIn("Marketing is the biggest overspend.", assistant["content"])
        self.assertIn("group_by(dimension=department)", assistant["content"])

    def test_assistant_with_only_tool_calls_is_kept(self):
        # Tool calls but no narration text -> still useful context, kept.
        history = [{
            "role": "assistant",
            "content": "",
            "tool_calls": [{"name": "get_top_risks", "args": {"n": 3}}],
        }]
        out = build_input("And group those.", history)
        self.assertEqual(len(out), 2)
        self.assertIn("get_top_risks(n=3)", out[0]["content"])
