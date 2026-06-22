"""
Deterministic budget analysis.

ARCHITECTURAL CONTRACT (do not violate):
- EVERY number the product shows is computed HERE, in plain Python.
- The LLM/agent NEVER computes, estimates, or alters a figure. It only chooses
  which of these functions to call and narrates the structured result.
- These functions are pure: input -> output, no Django, no I/O, no LLM. That is
  what makes them unit-testable and what makes the product's numbers trustworthy.

This module is the heart of the submission. Keep it pure and well-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Literal

Severity = Literal["High", "Medium", "Low"]


@dataclass(frozen=True)
class LineItemData:
    """Plain value object so analysis never depends on the Django ORM."""
    department: str
    category: str
    budget: float
    actual: float

    @classmethod
    def from_model(cls, m) -> "LineItemData":
        return cls(
            department=m.department,
            category=m.category,
            budget=float(m.budget_amount),
            actual=float(m.actual_amount),
        )


@dataclass(frozen=True)
class VarianceRow:
    department: str
    category: str
    budget: float
    actual: float
    variance: float          # actual - budget  (positive = over budget)
    variance_pct: float      # variance / budget * 100  (0 if budget == 0)
    over_budget: bool
    severity: Severity

    def to_dict(self) -> dict:
        return asdict(self)


# --- severity policy -------------------------------------------------------
# Deterministic, documented thresholds. Severity is driven primarily by the
# ABSOLUTE euros over budget (a CFO cares first about money at risk), which also
# reproduces the brief's example table (15,000 -> High, 7,500 -> Medium). A very
# large RELATIVE overspend escalates small lines so a tiny-but-blown line isn't
# hidden. Under-budget items are never a risk.
HIGH_ABS = 10_000.0      # >= 10k over budget          -> High
MEDIUM_ABS = 5_000.0     # >= 5k  over budget          -> Medium
ESCALATE_PCT = 50.0      # small line but >= 50% over  -> at least Medium


def classify_severity(variance: float, variance_pct: float) -> Severity:
    """Pure severity rule. Only OVER-budget (variance > 0) can be a risk."""
    if variance <= 0:
        return "Low"
    if variance >= HIGH_ABS:
        return "High"
    if variance >= MEDIUM_ABS or variance_pct >= ESCALATE_PCT:
        return "Medium"
    return "Low"


def _pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100.0, 2)


def compute_variances(items: Iterable[LineItemData]) -> list[VarianceRow]:
    """Core computation: variance, % and severity for each line item."""
    rows: list[VarianceRow] = []
    for it in items:
        variance = round(it.actual - it.budget, 2)
        variance_pct = _pct(variance, it.budget)
        rows.append(
            VarianceRow(
                department=it.department,
                category=it.category,
                budget=round(it.budget, 2),
                actual=round(it.actual, 2),
                variance=variance,
                variance_pct=variance_pct,
                over_budget=variance > 0,
                severity=classify_severity(variance, variance_pct),
            )
        )
    # Most over-budget first — the reviewer's first question is "what's over budget".
    rows.sort(key=lambda r: r.variance, reverse=True)
    return rows


def group_variances(
    items: Iterable[LineItemData],
    dimension: Literal["department", "category"] = "department",
) -> list[dict]:
    """Aggregate budget/actual/variance by a dimension."""
    buckets: dict[str, dict] = {}
    for it in items:
        key = getattr(it, dimension)
        b = buckets.setdefault(
            key, {dimension: key, "budget": 0.0, "actual": 0.0}
        )
        b["budget"] += it.budget
        b["actual"] += it.actual
    out: list[dict] = []
    for b in buckets.values():
        variance = round(b["actual"] - b["budget"], 2)
        out.append(
            {
                dimension: b[dimension],
                "budget": round(b["budget"], 2),
                "actual": round(b["actual"], 2),
                "variance": variance,
                "variance_pct": _pct(variance, b["budget"]),
                "severity": classify_severity(variance, _pct(variance, b["budget"])),
            }
        )
    out.sort(key=lambda r: r["variance"], reverse=True)
    return out


def top_risks(items: Iterable[LineItemData], n: int = 3) -> list[dict]:
    """The n most severe over-budget rows (High before Medium, then by amount)."""
    sev_rank = {"High": 0, "Medium": 1, "Low": 2}
    rows = [r for r in compute_variances(items) if r.over_budget]
    rows.sort(key=lambda r: (sev_rank[r.severity], -r.variance))
    return [r.to_dict() for r in rows[:n]]


def simulate_change(
    items: Iterable[LineItemData],
    department: str,
    pct_change: float,
) -> dict:
    """
    What-if: adjust ACTUAL spend for one department by pct_change (e.g. -10 for
    a 10% cut), recompute totals. Returns before/after totals + delta.
    pct_change is a percentage: -10 means reduce by 10%.
    """
    items = list(items)
    before_actual = sum(it.actual for it in items)
    factor = 1.0 + (pct_change / 100.0)
    after_items = [
        LineItemData(
            it.department,
            it.category,
            it.budget,
            it.actual * factor if it.department == department else it.actual,
        )
        for it in items
    ]
    after_actual = sum(it.actual for it in after_items)
    total_budget = sum(it.budget for it in items)
    return {
        "department": department,
        "pct_change": pct_change,
        "total_budget": round(total_budget, 2),
        "actual_before": round(before_actual, 2),
        "actual_after": round(after_actual, 2),
        "delta": round(after_actual - before_actual, 2),
        "variance_before": round(before_actual - total_budget, 2),
        "variance_after": round(after_actual - total_budget, 2),
    }
