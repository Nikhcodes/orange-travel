"""Experiments for the three research questions and for tuning the model.

Tuning protocol (prevents overfitting on the reported numbers):
    1. Try every weight combination in WEIGHT_GRID on the 'ontwikkel' wishes only.
    2. Pick the best: most top-1 hits, then most top-3 hits, then the smallest
       change from the neutral weights (all 1.0) - simplest model wins a tie.
    3. Measure the chosen model ONCE on the 'test' wishes. Those are the numbers we report.
"""

import itertools

import pandas as pd

from src import config
from src.evaluation import evaluate_scenarios, summarize
from src.preprocessing import FEATURE_GROUPS, GROUP_CATEGORY, GROUP_COMPANION, GROUP_DAYS, GROUP_PRICE
from src.recommendation_engine import RecommendationEngine

WEIGHT_GRID = {
    GROUP_PRICE: [0.0, 0.25, 0.5, 0.75, 1.0],
    GROUP_DAYS: [0.5, 1.0, 1.5, 2.0],
    GROUP_COMPANION: [1.0, 1.5, 2.0, 3.0],
}


def split(scenarios: pd.DataFrame, name: str) -> pd.DataFrame:
    return scenarios[scenarios[config.COL_SPLIT] == name]


def score(destinations: pd.DataFrame, scenarios: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Evaluate one weight setting and return its key numbers."""
    summary = summarize(evaluate_scenarios(RecommendationEngine(destinations, weights=weights), scenarios))
    return {
        "top1": summary.top1_hits, "top3": summary.top3_hits, "n": summary.total_scenarios,
        "budget": summary.budget_compliance, "categorie": summary.category_match,
    }


def tune_weights(destinations: pd.DataFrame, dev_scenarios: pd.DataFrame) -> pd.DataFrame:
    """Grid search on the development wishes. Returns all results, best first."""
    rows = []
    groups = list(WEIGHT_GRID)
    for values in itertools.product(*(WEIGHT_GRID[g] for g in groups)):
        weights = dict(zip(groups, values))
        result = score(destinations, dev_scenarios, weights)
        rows.append({**weights, **result, "afwijking": sum(abs(v - 1.0) for v in values)})
    table = pd.DataFrame(rows)
    return table.sort_values(["top1", "top3", "afwijking"], ascending=[False, False, True]).reset_index(drop=True)


def best_weights(tuning_table: pd.DataFrame) -> dict[str, float]:
    best = tuning_table.iloc[0]
    return {group: float(best[group]) for group in WEIGHT_GRID}


def ablation(destinations: pd.DataFrame, scenarios: pd.DataFrame, base_weights: dict[str, float]) -> pd.DataFrame:
    """Research question 1: remove one feature group at a time and measure the effect."""
    rows = [{"variant": "alle kenmerken", **score(destinations, scenarios, base_weights)}]
    for group in FEATURE_GROUPS:
        if group == GROUP_CATEGORY:
            continue  # category is also a hard filter, so removing it from the distance changes nothing
        weights = {**base_weights, group: 0.0}
        rows.append({"variant": f"zonder {group}", **score(destinations, scenarios, weights)})
    return pd.DataFrame(rows)


def compare_models(destinations: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    """Research question 2: with and without price in the distance (budget filter always on)."""
    variants = {
        "Model A: prijs + dagen (gewichten 1)": {},
        "Model B: zonder prijs": {GROUP_PRICE: 0.0},
        "Eindmodel (getuned)": config.FINAL_WEIGHTS,
    }
    rows = []
    for name, weights in variants.items():
        for split_name in (config.SPLIT_DEV, config.SPLIT_TEST):
            rows.append({"model": name, "set": split_name, **score(destinations, split(scenarios, split_name), weights)})
    return pd.DataFrame(rows)
