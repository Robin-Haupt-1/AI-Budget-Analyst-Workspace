"""CRUD API smoke tests.

The deep finance logic is covered in test_analysis.py; these tests guard the
DRF wiring the reviewer's UI depends on: scenarios are nested with their line
items, line items can be filtered by scenario, and the full create/update/delete
cycle works. APITestCase gives each test a transactional DB (seeded by the data
migration) and a DRF `self.client`.
"""
from rest_framework.test import APITestCase

from budgets.models import Scenario


class ScenarioApiTests(APITestCase):
    def test_list_scenarios_includes_seeded_demo(self):
        resp = self.client.get("/api/scenarios/")
        self.assertEqual(resp.status_code, 200)
        names = {s["name"] for s in resp.json()}
        self.assertIn("Q2 2026 Operating Budget", names)

    def test_scenario_detail_nests_line_items(self):
        scenario = Scenario.objects.get(name="Q2 2026 Operating Budget")
        resp = self.client.get(f"/api/scenarios/{scenario.id}/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["period"], "Q2 2026")
        self.assertEqual(len(body["line_items"]), scenario.line_items.count())

    def test_line_items_filter_by_scenario(self):
        scenario = Scenario.objects.get(name="Q3 2026 Forecast")
        resp = self.client.get(f"/api/line-items/?scenario={scenario.id}")
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()
        self.assertTrue(rows)  # non-empty
        self.assertTrue(all(r["scenario"] == scenario.id for r in rows))

    def test_scenario_and_line_item_crud_cycle(self):
        # Create scenario
        created = self.client.post(
            "/api/scenarios/",
            {"name": "New Plan", "period": "Q4 2026", "description": "test"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        scenario_id = created.json()["id"]

        # Create a line item under it
        li = self.client.post(
            "/api/line-items/",
            {
                "scenario": scenario_id,
                "department": "Marketing",
                "category": "Paid Ads",
                "budget_amount": "1000.00",
                "actual_amount": "1500.00",
                "notes": "",
            },
            format="json",
        )
        self.assertEqual(li.status_code, 201)
        li_id = li.json()["id"]

        # Update it (PATCH)
        patched = self.client.patch(
            f"/api/line-items/{li_id}/", {"actual_amount": "1200.00"}, format="json"
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["actual_amount"], "1200.00")

        # Delete it
        self.assertEqual(self.client.delete(f"/api/line-items/{li_id}/").status_code, 204)

        # Delete the scenario
        self.assertEqual(self.client.delete(f"/api/scenarios/{scenario_id}/").status_code, 204)
        self.assertFalse(Scenario.objects.filter(id=scenario_id).exists())
