"""Feature engineering: turn tours and customer wishes into comparable number vectors.

Every tour and every customer becomes the same 9-number vector:

    [prijs, duur,                                   <- log-transformed, then StandardScaler
     type_Stad & omgeving, type_Binnenland & natuur, type_Rondreis,          <- one-hot (pd.get_dummies)
     gezelschap_Alleen, gezelschap_Stel, gezelschap_Gezin, gezelschap_Vrienden]

Design choices (see docs/technische_documentatie.md):
- Price and duration are log-transformed first. A difference between a 3-hour and a
  1-day tour matters more than between a 15- and 16-day round trip; the same holds
  for €30 vs €90 compared with €1,900 vs €1,960.
- A tour can suit several travel companions (multi-hot). Those ones are divided by
  their count, so a tour that suits everyone is not pushed away from every customer.
- The StandardScaler is fitted on the tours only and reused for every customer.
- One-hot columns come from pd.get_dummies on a Categorical with a FIXED category list,
  then are reindexed to the stored column order: a single customer row always gets
  exactly the same columns as the tours (no feature mismatch).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src import config

GROUP_PRICE, GROUP_DURATION, GROUP_TYPE, GROUP_COMPANION = "prijs", "duur", "type", "gezelschap"
FEATURE_GROUPS = [GROUP_PRICE, GROUP_DURATION, GROUP_TYPE, GROUP_COMPANION]
NEUTRAL_WEIGHTS = {group: 1.0 for group in FEATURE_GROUPS}


@dataclass
class CustomerProfile:
    """A validated customer wish. Budget is per person in euro."""

    budget: float
    days: float
    tour_type: str
    companion: str
    travelers: int = 1


def tour_midpoint_days(tours: pd.DataFrame) -> pd.Series:
    return (tours[config.COL_DAYS_MIN] + tours[config.COL_DAYS_MAX]) / 2


def _one_hot(values: pd.Series, allowed: list[str], prefix: str) -> pd.DataFrame:
    categorical = pd.Categorical(values, categories=allowed)
    return pd.get_dummies(categorical, prefix=prefix, dtype=float)


class FeaturePreprocessor:
    """Fits on the tours and transforms tours and customers identically.

    Args:
        weights: multiplier per feature group. A weight w multiplies the features, so the
            group's share of the squared distance is multiplied by w². Weight 0 removes it.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = {**NEUTRAL_WEIGHTS, **(weights or {})}
        unknown = set(self.weights) - set(FEATURE_GROUPS)
        if unknown:
            raise ValueError(f"Onbekende featuregroep(en): {sorted(unknown)}")
        self.scaler = StandardScaler()
        self.feature_columns: list[str] = []
        self.column_groups: dict[str, str] = {}
        self._fitted = False

    def fit(self, tours: pd.DataFrame) -> "FeaturePreprocessor":
        numeric = self._numeric(tours[config.COL_PRICE], tour_midpoint_days(tours))
        self.scaler.fit(numeric)
        type_cols = [f"type_{t}" for t in config.TYPES]
        comp_cols = [f"gezelschap_{c}" for c in config.COMPANIONS]
        self.feature_columns = [GROUP_PRICE, GROUP_DURATION, *type_cols, *comp_cols]
        self.column_groups = {GROUP_PRICE: GROUP_PRICE, GROUP_DURATION: GROUP_DURATION,
                              **{c: GROUP_TYPE for c in type_cols}, **{c: GROUP_COMPANION for c in comp_cols}}
        self._fitted = True
        return self

    @staticmethod
    def _numeric(price: pd.Series, days: pd.Series) -> pd.DataFrame:
        return pd.DataFrame({
            GROUP_PRICE: np.log1p(price.astype(float).to_numpy()),
            GROUP_DURATION: np.log2(days.astype(float).to_numpy()),
        })

    def _finish(self, numeric: pd.DataFrame, type_part: pd.DataFrame, companion_part: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("FeaturePreprocessor moet eerst gefit worden op de tours.")
        scaled = pd.DataFrame(self.scaler.transform(numeric), columns=numeric.columns)
        features = pd.concat([scaled, type_part.reset_index(drop=True), companion_part.reset_index(drop=True)], axis=1)
        features = features.reindex(columns=self.feature_columns, fill_value=0.0)
        for column, group in self.column_groups.items():
            features[column] = features[column] * self.weights[group]
        return features

    def transform_tours(self, tours: pd.DataFrame) -> pd.DataFrame:
        numeric = self._numeric(tours[config.COL_PRICE], tour_midpoint_days(tours))
        type_part = _one_hot(tours[config.COL_TYPE].reset_index(drop=True), config.TYPES, "type")
        multi_hot = tours[list(config.COMPANION_COLUMNS.values())].astype(float).reset_index(drop=True)
        multi_hot = multi_hot.div(multi_hot.sum(axis=1), axis=0)              # normalise: sums to 1
        multi_hot.columns = [f"gezelschap_{c}" for c in config.COMPANIONS]
        return self._finish(numeric, type_part, multi_hot)

    def transform_customer(self, customer: CustomerProfile) -> pd.DataFrame:
        """The budget goes into the price dimension: 'a trip around this price level'."""
        numeric = self._numeric(pd.Series([customer.budget]), pd.Series([customer.days]))
        type_part = _one_hot(pd.Series([customer.tour_type]), config.TYPES, "type")
        companion_part = _one_hot(pd.Series([customer.companion]), config.COMPANIONS, "gezelschap")
        return self._finish(numeric, type_part, companion_part)

    def distance_breakdown(self, customer_vector: np.ndarray, tour_vector: np.ndarray) -> dict[str, float]:
        """Share (0–1) of the squared distance caused by each feature group."""
        squared = (customer_vector - tour_vector) ** 2
        totals = {g: 0.0 for g in FEATURE_GROUPS}
        for value, column in zip(squared, self.feature_columns):
            totals[self.column_groups[column]] += float(value)
        total = sum(totals.values())
        return {g: (v / total if total else 0.0) for g, v in totals.items()}
