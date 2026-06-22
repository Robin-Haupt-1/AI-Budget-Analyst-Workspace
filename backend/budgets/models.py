from django.db import models


class Scenario(models.Model):
    name = models.CharField(max_length=200)
    period = models.CharField(max_length=50, blank=True, default="")  # e.g. "Q2 2026"
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class LineItem(models.Model):
    scenario = models.ForeignKey(
        Scenario, related_name="line_items", on_delete=models.CASCADE
    )
    department = models.CharField(max_length=120)
    category = models.CharField(max_length=120)
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.department} / {self.category}"
