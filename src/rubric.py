"""The written rubric that decides the expected best tour for a test wish.

It follows the group's priority order from the requirements (FR-07):
budget > duration > type of trip, followed by the travel companion.
It does NOT use KNN, scaling or distances, and is only used to label and check
data/test_wishes.csv - never by the recommender itself.

    1. Eligible = price per person <= budget.  None eligible -> "GEEN".
    2. Duration: prefer tours whose duration fits the wish. Buckets:
         0 = the wish lies within the tour's duration range
         1 = at most twice as long or half as long
         2 = further away
    3. Within the best duration bucket: prefer the chosen type of trip.
    4. Then: prefer tours that suit the travel companion.
    5. Then: the smallest exact duration difference.
    6. Then: the price closest to the budget (best use of the budget), then id.
"""

import pandas as pd

from src import config
from src.recommendation_engine import duration_gap


def _bucket(gap: float) -> int:
    return 0 if gap == 0 else (1 if gap <= 1 else 2)


def rubric_ranking(tours: pd.DataFrame, budget: float, days: float, tour_type: str, companion: str) -> pd.DataFrame:
    eligible = tours[tours[config.COL_PRICE] <= budget].copy()
    if eligible.empty:
        return eligible
    gaps = eligible.apply(lambda r: duration_gap(days, r[config.COL_DAYS_MIN], r[config.COL_DAYS_MAX]), axis=1)
    eligible = eligible.assign(
        _bucket=gaps.map(_bucket),
        _type=(eligible[config.COL_TYPE] != tour_type).astype(int),
        _companion=(eligible[config.COMPANION_COLUMNS[companion]] != 1).astype(int),
        _gap=gaps,
        _budget_gap=budget - eligible[config.COL_PRICE],
    )
    return eligible.sort_values(["_bucket", "_type", "_companion", "_gap", "_budget_gap", config.COL_ID])


def rubric_best(tours: pd.DataFrame, budget: float, days: float, tour_type: str, companion: str) -> str:
    ranked = rubric_ranking(tours, budget, days, tour_type, companion)
    return config.NO_RESULT_LABEL if ranked.empty else str(ranked.iloc[0][config.COL_NAME])


def relevant_names(tours: pd.DataFrame, budget: float, days: float, tour_type: str, companion: str) -> set[str]:
    """All tours that are equally good as the rubric's best on rules 1–4 (used for the confusion matrix)."""
    ranked = rubric_ranking(tours, budget, days, tour_type, companion)
    if ranked.empty:
        return set()
    best = ranked.iloc[0]
    same = ranked[(ranked["_bucket"] == best["_bucket"]) & (ranked["_type"] == best["_type"])
                  & (ranked["_companion"] == best["_companion"])]
    return set(same[config.COL_NAME])


def explain_rubric(tours: pd.DataFrame, budget: float, days: float, tour_type: str, companion: str) -> tuple[str, str, str]:
    """Return (expected, kind of wish, motivation) for a test wish."""
    ranked = rubric_ranking(tours, budget, days, tour_type, companion)
    if ranked.empty:
        cheapest = tours.sort_values(config.COL_PRICE).iloc[0]
        return config.NO_RESULT_LABEL, "geen resultaat", (
            f"Niets binnen €{budget:g} p.p.; goedkoopste is {cheapest[config.COL_NAME]} (€{cheapest[config.COL_PRICE]:g}).")
    best = ranked.iloc[0]
    if best["_bucket"] > 0 or best["_type"]:
        kind = "conflict"
    elif best["_companion"]:
        kind = "gezelschap ontbreekt"
    elif len(ranked) <= 3:
        kind = "krap budget"
    else:
        kind = "standaard"
    parts = [f"{len(ranked)} tour(s) binnen budget",
             "duur past" if best["_bucket"] == 0 else ("duur wijkt iets af" if best["_bucket"] == 1 else "duur wijkt sterk af"),
             "juiste soort reis" if not best["_type"] else f"andere soort ({best[config.COL_TYPE]})",
             "past bij gezelschap" if not best["_companion"] else "niet specifiek voor dit gezelschap"]
    return str(best[config.COL_NAME]), kind, "; ".join(parts) + "."
