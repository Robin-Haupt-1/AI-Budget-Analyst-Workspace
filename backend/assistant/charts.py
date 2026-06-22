"""
Pure presentation helper: turn a list of row dicts into a generic chart payload.

This module is deliberately separate from `budgets/analysis.py` (which does the
finance MATH) — that is the "decouple displaying charts from doing calculations"
seam. Analysis tools produce data; this builds a chart spec over already-computed
data; the agent only chooses chart type and which columns to plot. No numbers are
created here, so a chart can never disagree with the table it came from.

Pure (rows in -> spec out), so it is unit-tested without Django or an LLM.
"""
from __future__ import annotations

ALLOWED_CHART_TYPES = {"bar", "line", "pie"}


def infer_columns(rows: list[dict]) -> list[str]:
    return list(rows[0].keys()) if rows else []


def _is_numeric_column(rows: list[dict], key: str) -> bool:
    return bool(rows) and all(
        isinstance(r.get(key), (int, float)) and not isinstance(r.get(key), bool)
        for r in rows
    )


def build_chart(
    rows: list[dict],
    chart_type: str = "bar",
    x: str | None = None,
    y: str | None = None,
    title: str | None = None,
) -> dict:
    """Build a chart spec the frontend's generic <ChartWidget> renders.

    Falls back to sensible axes when the agent omits or mis-names them:
    x defaults to the first non-numeric column (the category/label), y to a
    numeric column, preferring 'variance' since that is the usual metric.
    """
    chart_type = chart_type if chart_type in ALLOWED_CHART_TYPES else "bar"
    columns = infer_columns(rows)
    numeric = [c for c in columns if _is_numeric_column(rows, c)]
    categorical = [c for c in columns if c not in numeric]

    if x not in columns:
        x = categorical[0] if categorical else (columns[0] if columns else None)
    if y not in columns or y not in numeric:
        y = "variance" if "variance" in numeric else (numeric[0] if numeric else None)

    return {
        "chart_type": chart_type,
        "x": x,
        "y": y,
        "title": title,
        "rows": rows,
    }
