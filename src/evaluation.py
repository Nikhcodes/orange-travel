"""Evaluation of the recommender against the predetermined test wishes.

All numbers are calculated from actual model output. Expected labels come from
data/test_wishes.csv (rubric, see src/rubric.py) and were fixed before tuning.

Metric definitions
    budget_compliance   share of all RECOMMENDED tours with price <= budget (FR-12 alternatives
                        are not recommendations and are counted separately as `n_over_budget_shown`)
    type_match          share of all recommended tours of the requested type
    top3_hit            expected best is among the recommendations
                        (expected 'GEEN': the bot gives zero recommendations)
    top1_hit            expected best is recommendation #1 (stricter, extra metric)

Confusion matrix (assignment requirement): for every (wish, tour) pair, is the tour
RELEVANT according to the rubric (rules 1–4) versus RECOMMENDED (in the top 3)?
"""

from dataclasses import dataclass

import pandas as pd

from src import config
from src.recommendation_engine import RecommendationEngine, validate_preferences
from src.rubric import relevant_names

REQUIRED_BUDGET_COMPLIANCE = 1.00
REQUIRED_TYPE_MATCH = 0.90
REQUIRED_TOP3 = 0.80


@dataclass
class EvaluationSummary:
    total_wishes: int
    total_recommendations: int
    over_budget_shown: int
    budget_compliance: float
    type_match: float
    top3_hits: int
    top1_hits: int

    @property
    def top3_rate(self) -> float:
        return self.top3_hits / self.total_wishes

    @property
    def top1_rate(self) -> float:
        return self.top1_hits / self.total_wishes

    @property
    def passes_budget(self) -> bool:
        return self.budget_compliance >= REQUIRED_BUDGET_COMPLIANCE

    @property
    def passes_type(self) -> bool:
        return self.type_match >= REQUIRED_TYPE_MATCH

    @property
    def passes_top3(self) -> bool:
        return self.top3_rate >= REQUIRED_TOP3


def evaluate_wishes(engine: RecommendationEngine, wishes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, wish in wishes.iterrows():
        customer = validate_preferences(wish[config.COL_BUDGET], wish[config.COL_WISH_DAYS], wish[config.COL_WISH_TYPE],
                                        wish[config.COL_WISH_COMPANION], wish.get(config.COL_TRAVELERS))
        result = engine.recommend(customer)
        names = [r.name for r in result.recommendations]
        expected = wish.get(config.COL_EXPECTED, "?")
        if expected == config.NO_RESULT_LABEL:
            top3 = top1 = not names
        else:
            top3, top1 = expected in names, bool(names) and names[0] == expected
        rows.append({
            config.COL_WISH_ID: wish.get(config.COL_WISH_ID, "-"),
            config.COL_BUDGET: customer.budget, config.COL_WISH_DAYS: customer.days,
            config.COL_WISH_TYPE: customer.tour_type, config.COL_WISH_COMPANION: customer.companion,
            config.COL_TRAVELERS: customer.travelers,
            config.COL_WISH_KIND: wish.get(config.COL_WISH_KIND, "-"), config.COL_SPLIT: wish.get(config.COL_SPLIT, "-"),
            config.COL_EXPECTED: expected, "aanbevolen": names, "n_aanbevolen": len(names),
            "n_binnen_budget": sum(r.price <= customer.budget for r in result.recommendations),
            "n_juiste_type": sum(r.tour_type == customer.tour_type for r in result.recommendations),
            "n_boven_budget_getoond": len(result.over_budget),
            "plek1": names[0] if names else config.NO_RESULT_LABEL, "top1_hit": top1, "top3_hit": top3,
        })
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> EvaluationSummary:
    n = int(results["n_aanbevolen"].sum())
    return EvaluationSummary(
        total_wishes=len(results), total_recommendations=n,
        over_budget_shown=int(results["n_boven_budget_getoond"].sum()),
        budget_compliance=float(results["n_binnen_budget"].sum() / n) if n else 1.0,
        type_match=float(results["n_juiste_type"].sum() / n) if n else 1.0,
        top3_hits=int(results["top3_hit"].sum()), top1_hits=int(results["top1_hit"].sum()),
    )


@dataclass
class RelevanceMatrix:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / (self.tp + self.fp + self.fn + self.tn)

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame([[self.tp, self.fn], [self.fp, self.tn]],
                            index=["Relevant", "Niet relevant"], columns=["Aanbevolen", "Niet aanbevolen"])


def relevance_matrix(results: pd.DataFrame, tours: pd.DataFrame) -> RelevanceMatrix:
    tp = fp = fn = tn = 0
    all_names = set(tours[config.COL_NAME])
    for _, row in results.iterrows():
        relevant = relevant_names(tours, row[config.COL_BUDGET], row[config.COL_WISH_DAYS],
                                  row[config.COL_WISH_TYPE], row[config.COL_WISH_COMPANION])
        recommended = set(row["aanbevolen"])
        tp += len(relevant & recommended)
        fp += len(recommended - relevant)
        fn += len(relevant - recommended)
        tn += len(all_names - relevant - recommended)
    return RelevanceMatrix(tp, fp, fn, tn)


def results_by_kind(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(config.COL_WISH_KIND).agg(
        wensen=(config.COL_WISH_ID, "count"), top1=("top1_hit", "mean"), top3=("top3_hit", "mean"))
    return grouped.reset_index().sort_values("wensen", ascending=False)
