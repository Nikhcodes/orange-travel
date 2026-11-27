"""The written rubric that determines the expected best destination of a test wish.

This is a human-style decision rule, written down BEFORE the model was tuned.
It does not use KNN, scaling or distances. It is only used to create and check
the labels in data/test_customers.csv, never by the recommender itself.

    1. Eligible = right category AND price <= budget.  None -> "GEEN".
    2. Prefer destinations suitable for the customer's travel companion (if any).
    3. Choose the smallest difference between destination days and desired days.
    4. Tie-break: the price closest to the budget (best use of the budget).
"""

import pandas as pd

from src import config


def rubric_best(destinations: pd.DataFrame, budget: float, days: int, category: str, companion: str) -> str:
    """Return the name of the best destination according to the rubric (or NO_RESULT_LABEL)."""
    eligible = destinations[
        (destinations[config.COL_CATEGORY] == category) & (destinations[config.COL_PRICE] <= budget)
    ]
    if eligible.empty:
        return config.NO_RESULT_LABEL

    companion_match = eligible[eligible[config.COL_COMPANION] == companion]
    pool = companion_match if not companion_match.empty else eligible

    ranked = pool.assign(
        day_gap=(pool[config.COL_DAYS] - days).abs(),
        budget_gap=budget - pool[config.COL_PRICE],
    ).sort_values(["day_gap", "budget_gap", config.COL_ID])
    return str(ranked.iloc[0][config.COL_NAME])


def explain_rubric(destinations: pd.DataFrame, budget: float, days: int, category: str, companion: str) -> tuple[str, str, str]:
    """Return (expected_best, scenario_type, motivation) for one wish."""
    best = rubric_best(destinations, budget, days, category, companion)
    of_category = destinations[destinations[config.COL_CATEGORY] == category]
    eligible = of_category[of_category[config.COL_PRICE] <= budget]

    if best == config.NO_RESULT_LABEL:
        cheapest = of_category.sort_values(config.COL_PRICE).iloc[0]
        return best, "geen resultaat", (
            f"Geen {category.lower()}-bestemming binnen ${budget:.0f}; goedkoopste is "
            f"{cheapest[config.COL_NAME]} (${cheapest[config.COL_PRICE]}). Verwacht: nul aanbevelingen."
        )

    match = eligible[eligible[config.COL_COMPANION] == companion]
    row = destinations[destinations[config.COL_NAME] == best].iloc[0]
    if match.empty:
        scenario_type = "conflict"
    elif len(eligible) <= 2:
        scenario_type = "krap budget"
    else:
        # A trade-off exists when the companion match closest to the budget is NOT the rubric choice.
        priciest_match = match.sort_values(config.COL_PRICE).iloc[-1][config.COL_NAME]
        scenario_type = "afweging" if priciest_match != best else "standaard"

    parts = [f"{len(eligible)} {category.lower()}-bestemming(en) binnen budget"]
    parts.append(
        f"{len(match)} geschikt voor {companion.lower()}" if len(match)
        else f"geen enkele geschikt voor {companion.lower()}"
    )
    parts.append(f"{best} ligt het dichtst bij {days} dagen ({row[config.COL_DAYS]} dagen)")
    return best, scenario_type, "; ".join(parts) + "."
