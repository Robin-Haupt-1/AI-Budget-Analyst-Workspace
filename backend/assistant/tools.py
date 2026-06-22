"""
Agent tools, organised around a clean split:

  DATA / CALCULATION tools  ->  return a {data_table} payload (rows + columns)
  PRESENTATION tool         ->  show_chart(): visualises a previously-loaded
                                dataset as a generic chart

Every number is still computed by the deterministic `budgets.analysis` module (or
read straight from the DB). The LLM never computes — it loads data, then decides
which chart, if any, to draw over it. show_chart() draws over data that a data
tool already cached in the run context, so a chart can't contain a number the
tables didn't, and the agent only picks chart type + columns (never values).

This uses the OpenAI Agents SDK `@function_tool` decorator
and `RunContextWrapper`. The context object is shared across tool calls within a
single run, which is what makes the load-then-chart handoff work.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from asgiref.sync import sync_to_async
from agents import function_tool, RunContextWrapper

from budgets.models import LineItem, Scenario
from budgets.analysis import (
    LineItemData,
    compute_variances,
    group_variances,
    top_risks,
    simulate_change,
)
from .charts import build_chart
from .cards import simulation_card


@dataclass
class BudgetContext:
    """Passed into Runner.run(context=...). Scopes tools to one scenario and
    caches each data tool's rows under a name so show_chart() can plot them."""
    scenario_id: int
    datasets: dict[str, list[dict]] = field(default_factory=dict)


@sync_to_async
def _load(scenario_id: int, department: str = "", category: str = "") -> list[LineItemData]:
    qs = LineItem.objects.filter(scenario_id=scenario_id)
    if department:
        qs = qs.filter(department__iexact=department)
    if category:
        qs = qs.filter(category__iexact=category)
    return [LineItemData.from_model(m) for m in qs]


def _filter_suffix(department: str, category: str) -> str:
    bits = [b for b in (department, category) if b]
    return f" ({', '.join(bits)})" if bits else ""


def _table(ctx: RunContextWrapper[BudgetContext], name: str,
           rows: list[dict], title: str) -> dict:
    """Cache rows under `name` and return a generic data-table widget payload."""
    ctx.context.datasets[name] = rows
    columns = list(rows[0].keys()) if rows else []
    return {
        "widget_kind": "data_table",
        "data": {"name": name, "title": title, "columns": columns, "rows": rows},
    }


# --- data loading ----------------------------------------------------------
@sync_to_async
def _list_scenarios() -> list[dict]:
    return [
        {"id": s.id, "name": s.name, "period": s.period,
         "line_items": s.line_items.count()}
        for s in Scenario.objects.all()
    ]


@function_tool
async def list_scenarios(ctx: RunContextWrapper[BudgetContext]) -> dict:
    """List every budget scenario (id, name, period, line-item count).
    Use to answer 'what scenarios exist'.

    RENDERS: a table titled "Budget scenarios" (one row per scenario) directly in
    the chat. The user already sees every row — do not reprint or list them; just
    give a one-line takeaway."""
    rows = await _list_scenarios()
    return _table(ctx, "scenarios", rows, "Budget scenarios")


@function_tool
async def load_scenario_data(ctx: RunContextWrapper[BudgetContext],
                            department: str = "", category: str = "") -> dict:
    """Load the line items for the current scenario (department, category, budget,
    actual, notes). Optionally filter by department and/or category
    (case-insensitive) — e.g. department='Marketing' for 'list just the marketing
    items'. The `notes` field is the reviewer's free-text explanation for a line
    (e.g. WHY it is over budget) — use it to explain variances, not just report them.

    RENDERS: a "Line items" table (one row per line item) in the chat. The user
    already sees the rows — summarise or interpret, don't reprint them."""
    items = await _load(ctx.context.scenario_id, department, category)
    rows = [{"department": it.department, "category": it.category,
             "budget": it.budget, "actual": it.actual, "notes": it.notes}
            for it in items]
    return _table(ctx, "line_items", rows, "Line items" + _filter_suffix(department, category))


# --- calculations (deterministic) ------------------------------------------
@function_tool
async def get_variances(ctx: RunContextWrapper[BudgetContext],
                        department: str = "", category: str = "") -> dict:
    """Compute budget-vs-actual variance and severity for every line item.
    Optionally filter by department and/or category (case-insensitive).
    Use for 'what is over budget' / 'show me the variances'.

    RENDERS: a "Budget variances" table with variance, % and severity per line item
    in the chat. The user already sees the full table — give the headline finding
    (e.g. which line is the biggest risk), don't restate the rows."""
    items = await _load(ctx.context.scenario_id, department, category)
    rows = [r.to_dict() for r in compute_variances(items)]
    return _table(ctx, "variances", rows, "Budget variances" + _filter_suffix(department, category))


@function_tool
async def group_by(ctx: RunContextWrapper[BudgetContext], dimension: str) -> dict:
    """Aggregate budget/actual/variance by 'department' or 'category'.
    Use for 'group this by department' / 'largest variances by category'.

    RENDERS: a "Variance by <dimension>" table (one row per group) in the chat. The
    user already sees every group — interpret the result, don't reprint the rows."""
    if dimension not in ("department", "category"):
        dimension = "department"
    items = await _load(ctx.context.scenario_id)
    rows = group_variances(items, dimension)
    name = f"variances_by_{dimension}"
    return _table(ctx, name, rows, f"Variance by {dimension}")


@function_tool
async def get_top_risks(ctx: RunContextWrapper[BudgetContext], n: int = 3) -> dict:
    """Return the n most severe over-budget items as a ranked list.
    Use for 'highlight the biggest risks'.

    RENDERS: a "Top N risks" table (the ranked over-budget items) in the chat. The
    user already sees the ranked list — call out the top risk in a sentence, don't
    re-list them."""
    items = await _load(ctx.context.scenario_id)
    rows = top_risks(items, n)
    return _table(ctx, "top_risks", rows, f"Top {n} risks")


@function_tool
async def simulate(ctx: RunContextWrapper[BudgetContext],
                   department: str, pct_change: float) -> dict:
    """What-if: change a department's ACTUAL spend by pct_change percent
    (e.g. -10 = reduce 10%) and recompute totals. Use for 'what would happen if...'.

    RENDERS: a stat card showing before/after totals and the delta in the chat. The
    user already sees the figures on the card — state the conclusion (does it close
    the gap?), don't recite the before/after numbers."""
    items = await _load(ctx.context.scenario_id)
    result = simulate_change(items, department, pct_change)
    return {"widget_kind": "stat_card", "data": simulation_card(result)}


# --- presentation ----------------------------------------------------------
@function_tool
async def show_chart(ctx: RunContextWrapper[BudgetContext], dataset: str,
                     chart_type: str = "bar", x: str = "", y: str = "",
                     title: str = "") -> dict:
    """Visualise a dataset that a data/calculation tool already returned.

    `dataset` is the name from that tool (e.g. 'variances_by_department',
    'variances', 'top_risks', 'line_items', 'scenarios'). `chart_type` is
    'bar', 'line', or 'pie'. x/y are column names to plot (sensible defaults are
    chosen if omitted). Run the relevant data tool BEFORE charting.

    RENDERS: the chart itself in the chat. The user already sees the chart — don't
    describe it bar by bar; at most note the takeaway it makes obvious.
    """
    rows = ctx.context.datasets.get(dataset)
    if not rows:
        available = ", ".join(ctx.context.datasets) or "none yet"
        return {"error": f"No dataset '{dataset}'. Load it with a data tool first. "
                         f"Available: {available}."}
    chart = build_chart(rows, chart_type=chart_type, x=x or None, y=y or None,
                        title=title or dataset.replace("_", " "))
    return {"widget_kind": "chart", "data": chart}


@function_tool
async def chart_values(ctx: RunContextWrapper[BudgetContext],
                       labels: list[str], values: list[float],
                       chart_type: str = "bar", title: str = "") -> dict:
    """Render a chart from values you provide directly (no stored dataset needed).
    Use when you want to visualise specific numbers — every value MUST come from a
    tool result, never invented. `labels` and `values` are parallel lists of the
    same length; `chart_type` is 'bar', 'line', or 'pie'.

    RENDERS: the chart itself in the chat. The user already sees it — don't read the
    values back out; just give the takeaway if one is worth stating."""
    rows = [{"label": l, "value": v} for l, v in zip(labels, values)]
    chart = build_chart(rows, chart_type=chart_type, x="label", y="value",
                        title=title or "chart")
    return {"widget_kind": "chart", "data": chart}


ALL_TOOLS = [
    list_scenarios,
    load_scenario_data,
    get_variances,
    group_by,
    get_top_risks,
    simulate,
    show_chart,
    chart_values,
]
