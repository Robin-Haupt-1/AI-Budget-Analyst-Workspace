"""Demo budget data.

The seed data lives here as plain Python so it has a single source of truth, and
it is loaded through `load_seed_data()`, which is written to work with EITHER the
real models OR Django's *historical* models (`apps.get_model(...)`). That lets the
data migration (`migrations/0002_seed_demo_data.py`) reuse the exact same data and
logic — the migration is the canonical way the demo data gets in, so a plain
`migrate` produces a ready-to-demo database with no extra step.

The first scenario intentionally contains the brief's example rows
(Marketing/Paid Ads 50000/65000, Sales/Travel 20000/27500, ...) so the demo's
first question — "which areas are over budget?" — returns the obviously-correct
table and matches the analysis unit tests. The second scenario exists so the
scenario selector is meaningful (managing *multiple* scenarios is core scope).
"""
from __future__ import annotations

# Each scenario: metadata + its line items. Amounts are plain numbers; the
# DecimalField coerces them on save.
SEED_SCENARIOS = [
    {
        "name": "Q2 2026 Operating Budget",
        "period": "Q2 2026",
        "description": "Company-wide operating budget vs. actuals for Q2 2026.",
        "line_items": [
            ("Marketing", "Paid Ads", 50000, 65000,
             "Higher CPCs and an extra campaign pushed spend over plan."),
            ("Marketing", "Events", 25000, 41000,
             "Added a last-minute conference booth."),
            ("Sales", "Travel", 20000, 27500,
             "More on-site client visits than budgeted."),
            ("Sales", "Software", 12000, 11200,
             "Consolidated two CRM seats during the quarter."),
            ("Engineering", "Tools", 30000, 28500,
             "Came in slightly under plan."),
            ("Engineering", "Cloud Infra", 40000, 52000,
             "Traffic growth drove compute costs up."),
            ("Operations", "Office", 15000, 12000,
             "Renegotiated the office lease."),
            ("Customer Success", "Support Tooling", 18000, 18750,
             "Minor overage from an annual plan true-up."),
        ],
    },
    {
        "name": "Q3 2026 Forecast",
        "period": "Q3 2026",
        "description": "Forward-looking forecast scenario for planning Q3 2026.",
        "line_items": [
            ("Marketing", "Paid Ads", 60000, 58000,
             "Forecast assumes CPCs normalise."),
            ("Marketing", "Content", 20000, 23000,
             "Adding a freelance writer to scale the blog."),
            ("Sales", "Travel", 22000, 24000,
             "Two extra regional roadshows planned."),
            ("Engineering", "Cloud Infra", 45000, 61000,
             "Projected from current run-rate; biggest forecast risk."),
            ("Operations", "Facilities", 20000, 17000,
             "Hybrid-work plan lowers expected facilities spend."),
            ("Customer Success", "Software", 18000, 19500,
             "Renewal includes a seat expansion for the new CSM."),
        ],
    },
]

# Names used by the migration's reverse step so it only removes seeded rows.
SEED_SCENARIO_NAMES = [s["name"] for s in SEED_SCENARIOS]


def load_seed_data(Scenario, LineItem) -> int:
    """Idempotently create the demo scenarios.

    Works with real models or historical migration models. A scenario is created
    only if one with the same name does not already exist, so this is safe to run
    repeatedly (from the migration AND the `seed` management command). Returns the
    number of scenarios created.
    """
    created = 0
    for spec in SEED_SCENARIOS:
        if Scenario.objects.filter(name=spec["name"]).exists():
            continue
        scenario = Scenario.objects.create(
            name=spec["name"],
            period=spec["period"],
            description=spec["description"],
        )
        for dept, category, budget, actual, notes in spec["line_items"]:
            LineItem.objects.create(
                scenario=scenario,
                department=dept,
                category=category,
                budget_amount=budget,
                actual_amount=actual,
                notes=notes,
            )
        created += 1
    return created


def run() -> int:
    """Entry point for the `seed` management command (uses the real models)."""
    from .models import Scenario, LineItem

    return load_seed_data(Scenario, LineItem)
