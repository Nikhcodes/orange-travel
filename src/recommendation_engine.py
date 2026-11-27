"""KNN recommendation engine: distance ranking + hard business rules + explanations.

Flow for one customer:
    1. validate input
    2. transform customer to the same feature vector as the destinations
    3. NearestNeighbors computes the distance to ALL destinations (sorted)
    4. hard filters: price <= budget AND category == chosen category
    5. keep the first TOP_N that survive -> recommendations
    6. nothing survives -> no-result + cheapest in category (informational only)

Why distances to ALL destinations (step 3) instead of k=3?
    If we asked for only 3 neighbours and then filtered on budget, we could
    end up with 0 or 1 result while other affordable destinations exist.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from src import config
from src.preprocessing import CustomerProfile, FeaturePreprocessor


class InvalidPreferencesError(ValueError):
    """Raised when customer input is invalid (e.g. budget <= 0)."""


@dataclass
class Reason:
    """One building block of an explanation.

    The engine stores WHAT is true (a code + real values); the i18n module
    decides HOW it is phrased in Dutch or Sranan Tongo. This keeps the
    explanation honest: every sentence is generated from actual data.
    """

    code: str
    params: dict
    positive: bool = True


@dataclass
class Recommendation:
    """One recommended destination with everything the GUI needs."""

    rank: int
    destination_id: str
    name: str
    price: int
    days: int
    category: str
    companion: str
    distance: float
    remaining_budget: int
    distance_shares: dict[str, float]
    reasons: list[Reason] = field(default_factory=list)


@dataclass
class RecommendationResult:
    """Result for one customer: 0–3 recommendations, or an informational fallback."""

    customer: CustomerProfile
    recommendations: list[Recommendation]
    eligible_count: int
    cheapest_in_category: dict | None = None  # ONLY filled when there are 0 recommendations

    @property
    def has_results(self) -> bool:
        return len(self.recommendations) > 0


def validate_preferences(budget: float, days: int, category: str, companion: str) -> CustomerProfile:
    """Check customer input and return a CustomerProfile, or raise InvalidPreferencesError."""
    errors = []
    try:
        budget = float(budget)
        if not np.isfinite(budget) or budget <= 0:
            errors.append("budget_positive")
    except (TypeError, ValueError):
        errors.append("budget_positive")

    if isinstance(days, bool) or not isinstance(days, (int, np.integer)) or days < 1:
        errors.append("days_positive_int")
    if category not in config.CATEGORIES:
        errors.append("category_invalid")
    if companion not in config.COMPANIONS:
        errors.append("companion_invalid")

    if errors:
        raise InvalidPreferencesError(", ".join(errors))
    return CustomerProfile(budget=budget, days=int(days), category=category, companion=companion)


class RecommendationEngine:
    """KNN-based recommender for the Orange Travel destinations.

    Args:
        destinations: validated destination DataFrame (see data_loader).
        use_price: Model A (True) or Model B without price in the distance (False).
            The hard budget filter is active in BOTH models.
        weights: feature-group weights (see FeaturePreprocessor). None = the tuned
            config.FINAL_WEIGHTS; pass {} for neutral weights (all 1.0).
        top_n: maximum number of recommendations.
    """

    def __init__(
        self,
        destinations: pd.DataFrame,
        use_price: bool = True,
        weights: dict[str, float] | None = None,
        top_n: int = config.TOP_N,
    ) -> None:
        self.destinations = destinations.reset_index(drop=True)
        self.top_n = top_n
        if weights is None:
            weights = config.FINAL_WEIGHTS
        self.weights = weights
        self.preprocessor = FeaturePreprocessor(use_price=use_price, weights=weights).fit(self.destinations)
        self.destination_features = self.preprocessor.transform_destinations(self.destinations)

        self.model = NearestNeighbors(n_neighbors=len(self.destinations), metric="euclidean")
        self.model.fit(self.destination_features.to_numpy())

    # -------------------------------------------------------------- public
    def recommend(self, customer: CustomerProfile) -> RecommendationResult:
        """Return up to top_n recommendations that respect budget and category."""
        customer_vector = self.preprocessor.transform_customer(customer).to_numpy()
        distances, indices = self.model.kneighbors(customer_vector)

        ranking = self.destinations.iloc[indices[0]].copy()
        ranking["distance"] = distances[0]
        # Deterministic order for equal distances: cheaper first, then id.
        ranking = ranking.sort_values(["distance", config.COL_PRICE, config.COL_ID], kind="stable")

        eligible = ranking[
            (ranking[config.COL_PRICE] <= customer.budget)
            & (ranking[config.COL_CATEGORY] == customer.category)
        ]

        recommendations = [
            self._build_recommendation(rank, row, customer, customer_vector[0])
            for rank, (_, row) in enumerate(eligible.head(self.top_n).iterrows(), start=1)
        ]

        # Last line of defence: the budget rule is non-negotiable.
        assert all(r.price <= customer.budget for r in recommendations), "Budgetregel geschonden"

        cheapest = None
        if not recommendations:
            cheapest = self._cheapest_in_category(customer.category)

        return RecommendationResult(
            customer=customer,
            recommendations=recommendations,
            eligible_count=len(eligible),
            cheapest_in_category=cheapest,
        )

    def full_ranking(self, customer: CustomerProfile) -> pd.DataFrame:
        """All destinations with their distance, BEFORE filters (for teaching/debugging)."""
        customer_vector = self.preprocessor.transform_customer(customer).to_numpy()
        distances, indices = self.model.kneighbors(customer_vector)
        ranking = self.destinations.iloc[indices[0]].copy()
        ranking["distance"] = distances[0].round(3)
        ranking["binnen_budget"] = ranking[config.COL_PRICE] <= customer.budget
        ranking["juiste_soort"] = ranking[config.COL_CATEGORY] == customer.category
        return ranking.reset_index(drop=True)

    # ------------------------------------------------------------- helpers
    def _cheapest_in_category(self, category: str) -> dict:
        """Cheapest destination of a category. Informational only — never a recommendation."""
        subset = self.destinations[self.destinations[config.COL_CATEGORY] == category]
        row = subset.sort_values(config.COL_PRICE).iloc[0]
        return {
            "name": row[config.COL_NAME],
            "price": int(row[config.COL_PRICE]),
            "days": int(row[config.COL_DAYS]),
            "companion": row[config.COL_COMPANION],
        }

    def _build_recommendation(
        self, rank: int, row: pd.Series, customer: CustomerProfile, customer_vector: np.ndarray
    ) -> Recommendation:
        destination_vector = self.destination_features.iloc[row.name].to_numpy()
        price = int(row[config.COL_PRICE])
        return Recommendation(
            rank=rank,
            destination_id=row[config.COL_ID],
            name=row[config.COL_NAME],
            price=price,
            days=int(row[config.COL_DAYS]),
            category=row[config.COL_CATEGORY],
            companion=row[config.COL_COMPANION],
            distance=float(row["distance"]),
            remaining_budget=int(round(customer.budget - price)),
            distance_shares=self.preprocessor.distance_breakdown(customer_vector, destination_vector),
            reasons=build_reasons(row, customer),
        )


def build_reasons(row: pd.Series, customer: CustomerProfile) -> list[Reason]:
    """Create data-driven explanation building blocks for one destination.

    Mismatches are reported honestly (positive=False) instead of being hidden.
    """
    price = int(row[config.COL_PRICE])
    days = int(row[config.COL_DAYS])
    reasons = [Reason("category_match", {"category": customer.category})]

    if row[config.COL_COMPANION] == customer.companion:
        reasons.append(Reason("companion_match", {"companion": customer.companion}))
    else:
        reasons.append(
            Reason(
                "companion_mismatch",
                {"destination_companion": row[config.COL_COMPANION], "companion": customer.companion},
                positive=False,
            )
        )

    day_gap = days - customer.days
    if day_gap == 0:
        reasons.append(Reason("days_exact", {"days": days}))
    else:
        reasons.append(
            Reason(
                "days_longer" if day_gap > 0 else "days_shorter",
                {"days": days, "wish": customer.days, "gap": abs(day_gap)},
                positive=abs(day_gap) <= 2,
            )
        )

    reasons.append(
        Reason(
            "within_budget",
            {"price": price, "budget": int(round(customer.budget)), "remaining": int(round(customer.budget - price))},
        )
    )
    return reasons
