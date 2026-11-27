"""Tuning and the research questions.

Tuning protocol (prevents overfitting on the reported numbers):
    1. Try every weight combination in WEIGHT_GRID on the 'ontwikkel' wishes only.
    2. Keep only combinations that meet the assignment's criteria on that set
       (type match >= 90%, expected best in top 3 >= 80%). FR-07 (duration before type)
       pulls towards other types; this constraint keeps both requirements satisfied.
    3. Best = most top-1 hits, then most top-3 hits, then the smallest change from
       neutral weights (simplest model wins a tie).
    4. Measure the chosen model ONCE on the 'test' wishes; those numbers are reported.
"""

import itertools

import pandas as pd

from src import config
from src.evaluation import REQUIRED_TOP3, REQUIRED_TYPE_MATCH, evaluate_wishes, summarize
from src.preprocessing import FEATURE_GROUPS, GROUP_COMPANION, GROUP_DURATION, GROUP_PRICE, GROUP_TYPE
from src.recommendation_engine import RecommendationEngine

WEIGHT_GRID = {
    GROUP_PRICE: [0.0, 0.25, 0.5, 1.0],
    GROUP_DURATION: [1.0, 2.0, 3.0, 4.0],
    GROUP_TYPE: [0.5, 1.0, 1.5, 2.0],
    GROUP_COMPANION: [0.5, 1.0, 2.0],
}


def split(wishes: pd.DataFrame, name: str) -> pd.DataFrame:
    return wishes[wishes[config.COL_SPLIT] == name]


def score(tours: pd.DataFrame, wishes: pd.DataFrame, weights: dict[str, float]) -> dict:
    s = summarize(evaluate_wishes(RecommendationEngine(tours, weights=weights), wishes))
    return {"top1": s.top1_hits, "top3": s.top3_hits, "n": s.total_wishes,
            "type_match": round(s.type_match, 3), "budget": s.budget_compliance}


def tune_weights(tours: pd.DataFrame, dev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = list(WEIGHT_GRID)
    for values in itertools.product(*(WEIGHT_GRID[g] for g in groups)):
        weights = dict(zip(groups, values))
        rows.append({**weights, **score(tours, dev, weights), "afwijking": sum(abs(v - 1) for v in values)})
    table = pd.DataFrame(rows)
    table["voldoet"] = (table["type_match"] >= REQUIRED_TYPE_MATCH) & (table["top3"] >= REQUIRED_TOP3 * table["n"])
    return table.sort_values(["voldoet", "top1", "top3", "afwijking"],
                             ascending=[False, False, False, True]).reset_index(drop=True)


def best_weights(table: pd.DataFrame) -> dict[str, float]:
    return {g: float(table.iloc[0][g]) for g in WEIGHT_GRID}


def ablation(tours: pd.DataFrame, wishes: pd.DataFrame, base: dict[str, float]) -> pd.DataFrame:
    """Research question 1: remove one feature group at a time."""
    rows = [{"variant": "alle kenmerken", **score(tours, wishes, base)}]
    for group in FEATURE_GROUPS:
        rows.append({"variant": f"zonder {group}", **score(tours, wishes, {**base, group: 0.0})})
    return pd.DataFrame(rows)


def compare_models(tours: pd.DataFrame, wishes: pd.DataFrame) -> pd.DataFrame:
    """Research question 2: with and without budget/price in the distance (budget rule always on)."""
    variants = {"Model A: alle gewichten 1": {}, "Model B: zonder prijs": {GROUP_PRICE: 0.0},
                "Eindmodel (getuned)": config.FINAL_WEIGHTS}
    rows = []
    for name, weights in variants.items():
        for split_name in (config.SPLIT_DEV, config.SPLIT_TEST):
            rows.append({"model": name, "set": split_name, **score(tours, split(wishes, split_name), weights)})
    return pd.DataFrame(rows)
