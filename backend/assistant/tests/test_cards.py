"""Tests for the pure stat-card builders."""
from django.test import SimpleTestCase

from assistant.cards import simulation_card, stat_card


class StatCardTests(SimpleTestCase):
    def test_stat_card_shape(self):
        card = stat_card("Title", [{"label": "A", "value": 1}])
        self.assertEqual(card, {"title": "Title", "items": [{"label": "A", "value": 1}]})

    def test_simulation_card_title_and_items(self):
        result = {
            "department": "Marketing", "pct_change": -10,
            "actual_before": 106000, "actual_after": 99500,
            "delta": -6500, "variance_before": 1, "variance_after": -2000,
        }
        card = simulation_card(result)
        self.assertEqual(card["title"], "What-if: Marketing actual -10%")
        labels = [i["label"] for i in card["items"]]
        self.assertEqual(labels, ["Actual before", "Actual after", "Change", "Variance after"])

    def test_simulation_card_tone_reflects_reviewer_view(self):
        # Spending less and ending under budget are "good".
        good = simulation_card({
            "department": "Marketing", "pct_change": -10,
            "actual_before": 106000, "actual_after": 99500,
            "delta": -6500, "variance_before": 1, "variance_after": -2000,
        })
        tones = {i["label"]: i.get("tone") for i in good["items"]}
        self.assertEqual(tones["Change"], "good")
        self.assertEqual(tones["Variance after"], "good")

        # Spending more and staying over budget are "bad".
        bad = simulation_card({
            "department": "Marketing", "pct_change": 10,
            "actual_before": 106000, "actual_after": 116600,
            "delta": 10600, "variance_before": 1, "variance_after": 30000,
        })
        tones = {i["label"]: i.get("tone") for i in bad["items"]}
        self.assertEqual(tones["Change"], "bad")
        self.assertEqual(tones["Variance after"], "bad")
