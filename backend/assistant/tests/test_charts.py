"""Tests for the pure chart-spec builder (decoupled from analysis)."""
from django.test import SimpleTestCase

from assistant.charts import build_chart

ROWS = [
    {"department": "Marketing", "budget": 75000, "actual": 106000, "variance": 31000},
    {"department": "Engineering", "budget": 70000, "actual": 80500, "variance": 10500},
]


class BuildChartTests(SimpleTestCase):
    def test_defaults_pick_category_x_and_variance_y(self):
        spec = build_chart(ROWS)
        self.assertEqual(spec["chart_type"], "bar")
        self.assertEqual(spec["x"], "department")   # first non-numeric column
        self.assertEqual(spec["y"], "variance")     # prefers 'variance'
        self.assertEqual(spec["rows"], ROWS)

    def test_invalid_chart_type_falls_back_to_bar(self):
        self.assertEqual(build_chart(ROWS, chart_type="donut")["chart_type"], "bar")

    def test_explicit_axes_are_respected(self):
        spec = build_chart(ROWS, chart_type="line", x="department", y="actual")
        self.assertEqual((spec["chart_type"], spec["x"], spec["y"]),
                         ("line", "department", "actual"))

    def test_bad_axis_names_are_replaced_with_sensible_defaults(self):
        spec = build_chart(ROWS, x="nope", y="also_nope")
        self.assertEqual(spec["x"], "department")
        self.assertEqual(spec["y"], "variance")

    def test_empty_rows_do_not_crash(self):
        spec = build_chart([])
        self.assertIsNone(spec["x"])
        self.assertIsNone(spec["y"])
        self.assertEqual(spec["rows"], [])
