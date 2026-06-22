"""Tests for the demo-data seed loader.

The loader is shared by the data migration and the `seed` management command, so
its idempotency is the contract that keeps `migrate`/re-seed safe. The data
migration runs when the test database is built, so the demo data already exists
at the start of each test.
"""
from django.test import TestCase

from budgets.models import Scenario, LineItem
from budgets.seed import SEED_SCENARIOS, load_seed_data, run


class SeedTests(TestCase):
    def test_migration_already_seeded_the_demo_data(self):
        self.assertEqual(Scenario.objects.count(), len(SEED_SCENARIOS))
        brief = Scenario.objects.get(name="Q2 2026 Operating Budget")
        paid_ads = brief.line_items.get(category="Paid Ads")
        self.assertEqual(float(paid_ads.budget_amount), 50000)
        self.assertEqual(float(paid_ads.actual_amount), 65000)

    def test_load_seed_data_is_idempotent(self):
        before_scenarios = Scenario.objects.count()
        before_items = LineItem.objects.count()
        created = load_seed_data(Scenario, LineItem)  # data already present
        self.assertEqual(created, 0)
        self.assertEqual(Scenario.objects.count(), before_scenarios)
        self.assertEqual(LineItem.objects.count(), before_items)

    def test_run_recreates_missing_scenarios(self):
        Scenario.objects.all().delete()
        created = run()
        self.assertEqual(created, len(SEED_SCENARIOS))
        self.assertEqual(Scenario.objects.count(), len(SEED_SCENARIOS))
        # Line item count equals the sum of every scenario's seeded items.
        expected_items = sum(len(s["line_items"]) for s in SEED_SCENARIOS)
        self.assertEqual(LineItem.objects.count(), expected_items)
