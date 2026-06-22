"""
Pure builders for the generic "stat card" widget — a titled list of
label/value items with an optional tone (good/bad) that drives colour.

Kept pure (dict in -> dict out) and separate from the tools so the presentation
mapping is unit-testable without Django or an LLM. The card is generic: any tool
can emit one; `simulation_card` is just the what-if's mapping onto it.
"""
from __future__ import annotations


def stat_card(title: str, items: list[dict]) -> dict:
    """Generic payload for the StatCard widget. Each item: {label, value, tone?}."""
    return {"title": title, "items": items}


def simulation_card(result: dict) -> dict:
    """Map a `simulate_change` result onto a generic stat card.

    Tone is from the reviewer's point of view: spending less (negative change) and
    ending under budget are 'good'; the opposite is 'bad'.
    """
    pct = result["pct_change"]
    delta = result["delta"]
    variance_after = result["variance_after"]
    sign = "+" if pct > 0 else ""
    items = [
        {"label": "Actual before", "value": result["actual_before"]},
        {"label": "Actual after", "value": result["actual_after"]},
        {"label": "Change", "value": delta, "tone": "good" if delta < 0 else "bad"},
        {"label": "Variance after", "value": variance_after,
         "tone": "bad" if variance_after > 0 else "good"},
    ]
    return stat_card(f"What-if: {result['department']} actual {sign}{pct}%", items)
