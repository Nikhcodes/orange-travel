"""KNN recommendation engine: distance ranking + budget rule + honest explanations.

Flow for one customer:
    1. transform the wish into the same feature vector as the tours
    2. NearestNeighbors computes the distance to ALL tours (sorted)
    3. budget rule: only tours with price <= budget per person can be recommended
    4. the first TOP_N that remain are the advice
    5. FR-12: if nothing fits the budget, the cheapest options are returned SEPARATELY
       as `over_budget`, always marked as above budget - never mixed into the advice.

Priority order (FR-07): budget (hard rule) > duration > type of trip > travel companion.
The type of trip is therefore a *soft* feature: when no trip of the chosen type fits the
duration, the advice may contain another type - and the explanation says so (FR-11).
"""

from dataclasses import dataclass, field
import math

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from src import config
from src.preprocessing import CustomerProfile, FeaturePreprocessor


class InvalidPreferencesError(ValueError):
    """Raised when a wish is invalid (e.g. budget <= 0). The message holds error codes."""


@dataclass
class Reason:
    """One explanation building block: WHAT is true (code + real values).

    `positive` = True means it matches the wish, False means it does not (FR-11).
    """

    code: str
    params: dict
    positive: bool = True


@dataclass
class Recommendation:
    rank: int
    tour_id: str
    name: str
    tour_type: str
    price: float
    duration_text: str
    days_min: float
    days_max: float
    min_persons: int
    intensity: str
    region: str
    description: str
    url: str
    note: str
    distance: float
    within_budget: bool
    budget_per_person: float
    travelers: int
    distance_shares: dict[str, float]
    reasons: list[Reason] = field(default_factory=list)

    @property
    def total_price(self) -> float:
        return self.price * self.travelers

    @property
    def remaining(self) -> float:
        return self.budget_per_person - self.price

    @property
    def fully_matches(self) -> bool:
        return all(r.positive for r in self.reasons)


@dataclass
class RecommendationResult:
    customer: CustomerProfile
    recommendations: list[Recommendation]          # always within budget
    eligible_count: int
    over_budget: list[Recommendation] = field(default_factory=list)  # FR-12, only when no advice fits

    @property
    def has_results(self) -> bool:
        return bool(self.recommendations)


def duration_gap(wish_days: float, days_min: float, days_max: float) -> float:
    """0 if the wish lies inside the tour's range, else the log2 distance to the nearest end.

    1.0 means 'twice as long or half as long'.
    """
    if days_min <= wish_days <= days_max:
        return 0.0
    nearest = days_min if wish_days < days_min else days_max
    return abs(math.log2(wish_days / nearest))


def validate_preferences(budget, days, tour_type, companion, travelers=None) -> CustomerProfile:
    """Check a wish. Raises InvalidPreferencesError with comma-separated error codes."""
    errors = []
    try:
        budget = float(budget)
        if not math.isfinite(budget) or budget <= 0:
            errors.append("budget")
    except (TypeError, ValueError):
        errors.append("budget")
    try:
        days = float(days)
        if not math.isfinite(days) or days <= 0 or days > 60:
            errors.append("days")
    except (TypeError, ValueError):
        errors.append("days")
    if tour_type not in config.TYPES:
        errors.append("type")
    if companion not in config.COMPANIONS:
        errors.append("companion")
    if travelers is None:
        travelers = {"Alleen": 1, "Stel": 2}.get(companion, 2)
    try:
        travelers = int(travelers)
        if not 1 <= travelers <= config.MAX_TRAVELERS:
            errors.append("travelers")
    except (TypeError, ValueError):
        errors.append("travelers")
    if errors:
        raise InvalidPreferencesError(", ".join(errors))
    return CustomerProfile(budget=budget, days=days, tour_type=tour_type, companion=companion, travelers=travelers)


class RecommendationEngine:
    """KNN recommender for the Orange Travel tours.

    Args:
        tours: validated tour DataFrame.
        weights: feature-group weights. None = the tuned config.FINAL_WEIGHTS;
            {} = neutral (all 1.0).
    """

    def __init__(self, tours: pd.DataFrame, weights: dict[str, float] | None = None, top_n: int = config.TOP_N):
        self.tours = tours.reset_index(drop=True)
        self.top_n = top_n
        self.weights = config.FINAL_WEIGHTS if weights is None else weights
        self.preprocessor = FeaturePreprocessor(self.weights).fit(self.tours)
        self.tour_features = self.preprocessor.transform_tours(self.tours)
        self.model = NearestNeighbors(n_neighbors=len(self.tours), metric="euclidean")
        self.model.fit(self.tour_features.to_numpy())

    def ranking(self, customer: CustomerProfile) -> tuple[pd.DataFrame, np.ndarray]:
        """All tours sorted by distance (before the budget rule)."""
        vector = self.preprocessor.transform_customer(customer).to_numpy()
        distances, indices = self.model.kneighbors(vector)
        ranked = self.tours.iloc[indices[0]].copy()
        ranked["distance"] = distances[0]
        ranked = ranked.sort_values(["distance", config.COL_PRICE, config.COL_ID], kind="stable")
        return ranked, vector[0]

    def recommend(self, customer: CustomerProfile) -> RecommendationResult:
        ranked, vector = self.ranking(customer)
        eligible = ranked[ranked[config.COL_PRICE] <= customer.budget]
        recs = [self._build(rank, row, customer, vector) for rank, (_, row) in
                enumerate(eligible.head(self.top_n).iterrows(), start=1)]
        assert all(r.price <= customer.budget for r in recs), "Budgetregel geschonden"

        over_budget = []
        if not recs:  # FR-12: cheapest options, clearly marked as above budget
            same_type = self.tours[self.tours[config.COL_TYPE] == customer.tour_type]
            pool = same_type if not same_type.empty else self.tours
            cheapest = ranked.loc[pool.sort_values([config.COL_PRICE, config.COL_ID]).index[: self.top_n]]
            cheapest = cheapest.sort_values([config.COL_PRICE, "distance"])
            over_budget = [self._build(rank, row, customer, vector) for rank, (_, row) in
                           enumerate(cheapest.iterrows(), start=1)]
        return RecommendationResult(customer, recs, len(eligible), over_budget)

    def _build(self, rank: int, row: pd.Series, customer: CustomerProfile, vector: np.ndarray) -> Recommendation:
        tour_vector = self.tour_features.iloc[row.name].to_numpy()
        return Recommendation(
            rank=rank, tour_id=row[config.COL_ID], name=row[config.COL_NAME], tour_type=row[config.COL_TYPE],
            price=float(row[config.COL_PRICE]), duration_text=row[config.COL_DURATION_TEXT],
            days_min=float(row[config.COL_DAYS_MIN]), days_max=float(row[config.COL_DAYS_MAX]),
            min_persons=int(row[config.COL_MIN_PERSONS]), intensity=row[config.COL_INTENSITY],
            region=row[config.COL_REGION], description=row[config.COL_DESCRIPTION], url=row[config.COL_URL],
            note=str(row[config.COL_NOTE] or ""), distance=float(row["distance"]),
            within_budget=float(row[config.COL_PRICE]) <= customer.budget, budget_per_person=customer.budget,
            travelers=customer.travelers,
            distance_shares=self.preprocessor.distance_breakdown(vector, tour_vector),
            reasons=build_reasons(row, customer),
        )


def build_reasons(row: pd.Series, customer: CustomerProfile) -> list[Reason]:
    """Data-driven explanation building blocks. Mismatches are reported, never hidden."""
    reasons: list[Reason] = []
    price = float(row[config.COL_PRICE])
    if price <= customer.budget:
        reasons.append(Reason("budget_ok", {"price": price, "remaining": customer.budget - price}))
    else:
        reasons.append(Reason("budget_over", {"price": price, "over": price - customer.budget}, positive=False))

    gap = duration_gap(customer.days, row[config.COL_DAYS_MIN], row[config.COL_DAYS_MAX])
    if gap == 0:
        reasons.append(Reason("duration_ok", {"duration": row[config.COL_DURATION_TEXT]}))
    else:
        longer = row[config.COL_DAYS_MIN] > customer.days
        reasons.append(Reason("duration_longer" if longer else "duration_shorter",
                              {"duration": row[config.COL_DURATION_TEXT], "wish": customer.days}, positive=gap <= 1))

    if row[config.COL_TYPE] == customer.tour_type:
        reasons.append(Reason("type_ok", {"type": customer.tour_type}))
    else:
        reasons.append(Reason("type_other", {"type": row[config.COL_TYPE], "wish": customer.tour_type}, positive=False))

    if int(row[config.COMPANION_COLUMNS[customer.companion]]) == 1:
        reasons.append(Reason("companion_ok", {"companion": customer.companion}))
    else:
        reasons.append(Reason("companion_other", {"companion": customer.companion}, positive=False))

    if customer.travelers < int(row[config.COL_MIN_PERSONS]):
        reasons.append(Reason("min_persons", {"min": int(row[config.COL_MIN_PERSONS]), "travelers": customer.travelers},
                              positive=False))
    if row[config.COL_INTENSITY] == "hoog":
        reasons.append(Reason("intensity_high", {}, positive=True))
    return reasons
