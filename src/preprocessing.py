"""Feature engineering: turn destinations and customers into comparable number vectors.

Every destination and every customer becomes the same vector:

    [prijs_scaled, dagen_scaled,
     soort_Strand, soort_Natuur, soort_Stad,
     geschikt_voor_Alleen, geschikt_voor_Stel, geschikt_voor_Gezin, geschikt_voor_Vrienden]

Two rules prevent the classic training/prediction mismatch:
    1. The StandardScaler is fitted ONLY on the destination dataset and then
       reused (transform, never fit) for every customer.
    2. One-hot columns are built with pd.get_dummies() on a Categorical with a
       FIXED list of categories and then reindexed to the stored column order,
       so a single customer row always gets all 7 one-hot columns.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src import config

# Feature groups: used for weighting, ablation (research question 1) and
# for explaining which part of the profile caused the distance.
GROUP_PRICE = "prijs"
GROUP_DAYS = "dagen"
GROUP_CATEGORY = "soort"
GROUP_COMPANION = "gezelschap"
FEATURE_GROUPS = [GROUP_PRICE, GROUP_DAYS, GROUP_CATEGORY, GROUP_COMPANION]

DEFAULT_WEIGHTS: dict[str, float] = {group: 1.0 for group in FEATURE_GROUPS}


@dataclass
class CustomerProfile:
    """The four customer preferences, already validated by the engine."""

    budget: float
    days: int
    category: str
    companion: str


def _one_hot(values: pd.Series, allowed: list[str], prefix: str) -> pd.DataFrame:
    """One-hot encode with pd.get_dummies using a fixed category list.

    Making the column categorical with all allowed values guarantees that
    get_dummies creates a column for every value, even if it does not occur
    in ``values`` (for example a single customer row).
    """
    categorical = pd.Categorical(values, categories=allowed)
    return pd.get_dummies(categorical, prefix=prefix, dtype=float)


class FeaturePreprocessor:
    """Fits on the destination dataset and transforms destinations and customers identically.

    Args:
        use_price: include price in the distance (Model A = True, Model B = False).
        weights: optional multiplier per feature group. A weight w multiplies the
            feature values, so the group's contribution to the squared distance
            is multiplied by w². Weight 0 removes the group (ablation).
    """

    def __init__(self, use_price: bool = True, weights: dict[str, float] | None = None) -> None:
        self.use_price = use_price
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        if not use_price:
            self.weights[GROUP_PRICE] = 0.0

        unknown = set(self.weights) - set(FEATURE_GROUPS)
        if unknown:
            raise ValueError(f"Onbekende featuregroep(en): {sorted(unknown)}")

        self.scaler = StandardScaler()
        self.feature_columns: list[str] = []
        self.column_groups: dict[str, str] = {}
        self._is_fitted = False

    # ------------------------------------------------------------------ fit
    def fit(self, destinations: pd.DataFrame) -> "FeaturePreprocessor":
        """Learn mean/std of price and days and fix the feature column order."""
        self.scaler.fit(destinations[[config.COL_PRICE, config.COL_DAYS]].astype(float))

        category_cols = [f"{config.COL_CATEGORY}_{c}" for c in config.CATEGORIES]
        companion_cols = [f"{config.COL_COMPANION}_{c}" for c in config.COMPANIONS]
        self.feature_columns = [config.COL_PRICE, config.COL_DAYS, *category_cols, *companion_cols]

        self.column_groups = {config.COL_PRICE: GROUP_PRICE, config.COL_DAYS: GROUP_DAYS}
        self.column_groups.update({col: GROUP_CATEGORY for col in category_cols})
        self.column_groups.update({col: GROUP_COMPANION for col in companion_cols})

        self._is_fitted = True
        return self

    # ------------------------------------------------------------ transform
    def _build(self, price: pd.Series, days: pd.Series, category: pd.Series, companion: pd.Series) -> pd.DataFrame:
        """Shared transformation for destinations and customers (no duplicate logic)."""
        if not self._is_fitted:
            raise RuntimeError("FeaturePreprocessor moet eerst gefit worden op de bestemmingen.")

        numeric = pd.DataFrame({config.COL_PRICE: price.astype(float), config.COL_DAYS: days.astype(float)})
        scaled = pd.DataFrame(self.scaler.transform(numeric), columns=numeric.columns)

        features = pd.concat(
            [
                scaled,
                _one_hot(category, config.CATEGORIES, config.COL_CATEGORY),
                _one_hot(companion, config.COMPANIONS, config.COL_COMPANION),
            ],
            axis=1,
        )
        # Safety net: same columns, same order as during fit.
        features = features.reindex(columns=self.feature_columns, fill_value=0.0)

        for column, group in self.column_groups.items():
            features[column] *= self.weights[group]
        return features

    def transform_destinations(self, destinations: pd.DataFrame) -> pd.DataFrame:
        """Feature matrix for all destinations (one row per destination)."""
        return self._build(
            destinations[config.COL_PRICE].reset_index(drop=True),
            destinations[config.COL_DAYS].reset_index(drop=True),
            destinations[config.COL_CATEGORY].reset_index(drop=True),
            destinations[config.COL_COMPANION].reset_index(drop=True),
        )

    def transform_customer(self, customer: CustomerProfile) -> pd.DataFrame:
        """Feature vector (1 row) for a customer.

        The budget is placed in the price dimension: we interpret it as the
        price level the customer is willing to pay (design decision 1).
        """
        return self._build(
            pd.Series([customer.budget]),
            pd.Series([customer.days]),
            pd.Series([customer.category]),
            pd.Series([customer.companion]),
        )

    # ------------------------------------------------------------- explain
    def distance_breakdown(self, customer_vector: np.ndarray, destination_vector: np.ndarray) -> dict[str, float]:
        """Split the squared Euclidean distance into one share per feature group.

        Returns the fraction (0–1) of the total squared distance caused by each
        group. Used for explanations and for research question 1.
        """
        squared = (customer_vector - destination_vector) ** 2
        totals = {group: 0.0 for group in FEATURE_GROUPS}
        for value, column in zip(squared, self.feature_columns):
            totals[self.column_groups[column]] += float(value)
        total = sum(totals.values())
        if total == 0:
            return totals
        return {group: value / total for group, value in totals.items()}
