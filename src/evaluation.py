"""Evaluation of the recommender against the predetermined test scenarios.

All percentages are calculated from the actual model output; nothing is
hard-coded. The expected labels come from test_customers.csv and were fixed
before the model existed (see scripts/validate_datasets.py for the rubric).

Metric definitions:
    budget_compliance   share of ALL recommended items with price <= budget
    category_match      share of ALL recommended items in the chosen category
    top3_hit            expected best is among the recommendations
                        (for expected 'GEEN': the system returns zero recommendations)
    top1_hit            expected best is recommendation #1 (stricter, extra metric)

Confusion matrices (assignment requirement):
    relevance matrix    for every (wish, destination) pair: is the destination RELEVANT
                        according to the rubric (affordable, right category, suitable for
                        the companion if such a trip exists) versus is it RECOMMENDED
                        (in the top 3)? -> TP / FP / FN / TN, precision, recall, F1.
    companion matrix    desired travel companion versus the 'geschikt_voor' of the #1
                        recommendation. Shows whether the model respects who you travel with.
"""

from dataclasses import dataclass

import pandas as pd

from src import config
from src.recommendation_engine import RecommendationEngine, validate_preferences

# Assignment success criteria.
REQUIRED_BUDGET_COMPLIANCE = 1.00
REQUIRED_CATEGORY_MATCH = 0.90
REQUIRED_TOP3 = 0.80


@dataclass
class EvaluationSummary:
    total_scenarios: int
    total_recommendations: int
    budget_compliance: float
    category_match: float
    top3_hits: int
    top1_hits: int

    @property
    def top3_rate(self) -> float:
        return self.top3_hits / self.total_scenarios

    @property
    def top1_rate(self) -> float:
        return self.top1_hits / self.total_scenarios

    @property
    def passes_budget(self) -> bool:
        return self.budget_compliance >= REQUIRED_BUDGET_COMPLIANCE

    @property
    def passes_category(self) -> bool:
        return self.category_match >= REQUIRED_CATEGORY_MATCH

    @property
    def passes_top3(self) -> bool:
        return self.top3_rate >= REQUIRED_TOP3

    @property
    def passes_all(self) -> bool:
        return self.passes_budget and self.passes_category and self.passes_top3


def evaluate_scenarios(engine: RecommendationEngine, scenarios: pd.DataFrame) -> pd.DataFrame:
    """Run every scenario through the engine and return one result row per scenario."""
    rows = []
    for _, scenario in scenarios.iterrows():
        customer = validate_preferences(
            scenario[config.COL_BUDGET],
            int(scenario[config.COL_WISH_DAYS]),
            scenario[config.COL_WISH_CATEGORY],
            scenario[config.COL_WISH_COMPANION],
        )
        result = engine.recommend(customer)
        names = [rec.name for rec in result.recommendations]
        expected = scenario.get(config.COL_EXPECTED, "?")

        if expected == config.NO_RESULT_LABEL:
            top3_hit = top1_hit = len(names) == 0
        else:
            top3_hit = expected in names
            top1_hit = bool(names) and names[0] == expected

        rows.append(
            {
                config.COL_SCENARIO_ID: scenario[config.COL_SCENARIO_ID],
                config.COL_BUDGET: customer.budget,
                config.COL_WISH_DAYS: customer.days,
                config.COL_WISH_CATEGORY: customer.category,
                config.COL_WISH_COMPANION: customer.companion,
                config.COL_SCENARIO_TYPE: scenario.get(config.COL_SCENARIO_TYPE, "-"),
                config.COL_SPLIT: scenario.get(config.COL_SPLIT, "-"),
                config.COL_EXPECTED: expected,
                "recommended": names,
                "n_recommended": len(names),
                "n_within_budget": sum(rec.price <= customer.budget for rec in result.recommendations),
                "n_right_category": sum(rec.category == customer.category for rec in result.recommendations),
                "top1": names[0] if names else config.NO_RESULT_LABEL,
                "top1_hit": top1_hit,
                "top3_hit": top3_hit,
            }
        )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> EvaluationSummary:
    """Calculate the success metrics from the per-scenario results."""
    total_recs = int(results["n_recommended"].sum())
    # With zero recommendations there is nothing that can violate the rule.
    budget = results["n_within_budget"].sum() / total_recs if total_recs else 1.0
    category = results["n_right_category"].sum() / total_recs if total_recs else 1.0
    return EvaluationSummary(
        total_scenarios=len(results),
        total_recommendations=total_recs,
        budget_compliance=float(budget),
        category_match=float(category),
        top3_hits=int(results["top3_hit"].sum()),
        top1_hits=int(results["top1_hit"].sum()),
    )


def relevant_names(destinations: pd.DataFrame, budget: float, category: str, companion: str) -> set[str]:
    """Destinations that are relevant for a wish according to the rubric (rules 1 and 2)."""
    eligible = destinations[
        (destinations[config.COL_CATEGORY] == category) & (destinations[config.COL_PRICE] <= budget)
    ]
    match = eligible[eligible[config.COL_COMPANION] == companion]
    pool = match if not match.empty else eligible
    return set(pool[config.COL_NAME])


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

    def as_frame(self, labels: tuple[str, str] = ("Aanbevolen", "Niet aanbevolen"),
                 truth: tuple[str, str] = ("Relevant", "Niet relevant")) -> pd.DataFrame:
        return pd.DataFrame([[self.tp, self.fn], [self.fp, self.tn]], index=list(truth), columns=list(labels))


def relevance_matrix(results: pd.DataFrame, destinations: pd.DataFrame) -> RelevanceMatrix:
    """Count TP/FP/FN/TN over all (wish, destination) pairs."""
    tp = fp = fn = tn = 0
    all_names = set(destinations[config.COL_NAME])
    for _, row in results.iterrows():
        relevant = relevant_names(destinations, row[config.COL_BUDGET], row[config.COL_WISH_CATEGORY],
                                  row[config.COL_WISH_COMPANION])
        recommended = set(row["recommended"])
        tp += len(relevant & recommended)
        fp += len(recommended - relevant)
        fn += len(relevant - recommended)
        tn += len(all_names - relevant - recommended)
    return RelevanceMatrix(tp, fp, fn, tn)


def companion_matrix(results: pd.DataFrame, destinations: pd.DataFrame) -> pd.DataFrame:
    """Rows: desired companion. Columns: 'geschikt_voor' of the #1 recommendation."""
    companion_of = dict(zip(destinations[config.COL_NAME], destinations[config.COL_COMPANION]))
    with_result = results[results["n_recommended"] > 0]
    predicted = with_result["top1"].map(companion_of)
    matrix = pd.crosstab(
        pd.Categorical(with_result[config.COL_WISH_COMPANION], categories=config.COMPANIONS),
        pd.Categorical(predicted, categories=config.COMPANIONS),
        dropna=False,
    )
    matrix.index.name, matrix.columns.name = "gewenst", "plek 1 geschikt voor"
    return matrix


def results_by_type(results: pd.DataFrame) -> pd.DataFrame:
    """Top-1 and top-3 hit rates per scenario type."""
    grouped = results.groupby(config.COL_SCENARIO_TYPE).agg(
        scenarios=(config.COL_SCENARIO_ID, "count"),
        top1=("top1_hit", "mean"),
        top3=("top3_hit", "mean"),
    )
    return grouped.reset_index().sort_values("scenarios", ascending=False)
