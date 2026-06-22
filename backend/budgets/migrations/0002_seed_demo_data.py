"""Data migration that loads the demo budget scenarios.

This is the canonical way the seed data enters the database: `python manage.py
migrate` alone produces a ready-to-demo workspace, so `docker-compose up` needs no
separate seeding step. The data and the (idempotent) loading logic live in
`budgets/seed.py` as the single source of truth; here we just call it with the
historical models so the migration stays correct even if the models evolve later.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    from budgets.seed import load_seed_data

    Scenario = apps.get_model("budgets", "Scenario")
    LineItem = apps.get_model("budgets", "LineItem")
    load_seed_data(Scenario, LineItem)


def backwards(apps, schema_editor):
    from budgets.seed import SEED_SCENARIO_NAMES

    Scenario = apps.get_model("budgets", "Scenario")
    # Cascades to the scenarios' line items. Only removes the seeded rows so a
    # rollback never touches scenarios the reviewer created themselves.
    Scenario.objects.filter(name__in=SEED_SCENARIO_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("budgets", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
