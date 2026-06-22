"""
Tests focus on the DETERMINISTIC FINANCE LOGIC, not on Django plumbing.
This is deliberate: the numbers are the product's trust boundary, so they are
what we prove correct. Trivial CRUD has little signal; severity edges have a lot.

These are pure-Python checks with no database, so they run as a SimpleTestCase
(fast, and DB access is actively forbidden).
"""
from django.test import SimpleTestCase

from budgets.analysis import (
    LineItemData,
    classify_severity,
    compute_variances,
    group_variances,
    simulate_change,
    top_risks,
)

# The exact example from the brief, so the seeded demo and the tests agree.
BRIEF = [
    LineItemData("Marketing", "Paid Ads", 50000, 65000),
    LineItemData("Sales", "Travel", 20000, 27500),
    LineItemData("Engineering", "Tools", 30000, 28500),
]


class AnalysisTests(SimpleTestCase):
    def test_variance_basic_arithmetic(self):
        rows = {r.category: r for r in compute_variances(BRIEF)}
        self.assertEqual(rows["Paid Ads"].variance, 15000)
        self.assertEqual(rows["Travel"].variance, 7500)
        self.assertEqual(rows["Tools"].variance, -1500)
        self.assertFalse(rows["Tools"].over_budget)

    def test_variance_pct_and_zero_budget_guard(self):
        rows = {r.category: r for r in compute_variances(BRIEF)}
        self.assertEqual(rows["Paid Ads"].variance_pct, 30.0)        # 15000 / 50000
        z = compute_variances([LineItemData("X", "Y", 0, 100)])[0]
        self.assertEqual(z.variance, 100)
        self.assertEqual(z.variance_pct, 0.0)                        # no divide-by-zero

    def test_severity_matches_brief_example(self):
        # Reproduces the brief's illustrative table exactly.
        rows = {r.category: r for r in compute_variances(BRIEF)}
        self.assertEqual(rows["Paid Ads"].severity, "High")     # 15,000 over
        self.assertEqual(rows["Travel"].severity, "Medium")     # 7,500 over
        self.assertEqual(rows["Tools"].severity, "Low")         # under budget

    def test_severity_policy_edges(self):
        self.assertEqual(classify_severity(15000, 30.0), "High")     # large absolute
        self.assertEqual(classify_severity(7500, 37.5), "Medium")    # mid absolute
        self.assertEqual(classify_severity(-1500, -5.0), "Low")      # under budget never a risk
        self.assertEqual(classify_severity(12000, 4.0), "High")      # big euros, small %
        self.assertEqual(classify_severity(800, 80.0), "Medium")     # small line, blown %
        self.assertEqual(classify_severity(100, 5.0), "Low")

    def test_results_sorted_most_over_budget_first(self):
        rows = compute_variances(BRIEF)
        self.assertEqual([r.category for r in rows], ["Paid Ads", "Travel", "Tools"])

    def test_group_by_department(self):
        grouped = {g["department"]: g for g in group_variances(BRIEF, "department")}
        self.assertEqual(grouped["Marketing"]["variance"], 15000)
        self.assertEqual(grouped["Engineering"]["variance"], -1500)

    def test_top_risks_orders_by_severity_then_amount(self):
        risks = top_risks(BRIEF, n=2)
        self.assertEqual(risks[0]["category"], "Paid Ads")   # High, 15k
        self.assertEqual(risks[1]["category"], "Travel")     # Medium, 7.5k
        self.assertTrue(all(r["over_budget"] for r in risks))

    def test_simulate_reduction_changes_only_target_department(self):
        res = simulate_change(BRIEF, department="Marketing", pct_change=-10)
        self.assertEqual(res["delta"], -6500)                       # 65000 -> 58500
        self.assertEqual(res["actual_after"], res["actual_before"] - 6500)
