"""Automated proof of the business rules.

Run from the project root:  python -m pytest -v
"""

import itertools

import pandas as pd
import pytest

from src import config
from src.data_loader import load_destinations
from src.i18n import LANGUAGES, render_explanation
from src.preprocessing import CustomerProfile, FeaturePreprocessor
from src.recommendation_engine import InvalidPreferencesError, RecommendationEngine, validate_preferences

BUDGETS = [100, 380, 450, 650, 800, 1000, 1500, 2000, 2850, 3500, 5000, 10000]
DAYS = [1, 3, 5, 7, 10, 14, 21]


@pytest.fixture(scope="module")
def destinations() -> pd.DataFrame:
    return load_destinations()


@pytest.fixture(scope="module", params=[True, False], ids=["model_A", "model_B"])
def engine(request, destinations) -> RecommendationEngine:
    return RecommendationEngine(destinations, use_price=request.param)


def all_customers():
    for budget, days, category, companion in itertools.product(BUDGETS, DAYS, config.CATEGORIES, config.COMPANIONS):
        yield CustomerProfile(budget=budget, days=days, category=category, companion=companion)


def test_never_above_budget(engine):
    """1,008 customer combinations x 2 models: no recommendation may exceed the budget."""
    for customer in all_customers():
        for rec in engine.recommend(customer).recommendations:
            assert rec.price <= customer.budget


def test_always_right_category_and_max_three(engine):
    for customer in all_customers():
        result = engine.recommend(customer)
        assert len(result.recommendations) <= config.TOP_N
        assert all(rec.category == customer.category for rec in result.recommendations)


def test_returns_all_eligible_when_fewer_than_three(engine, destinations):
    """No affordable destination may be missed and none may be invented."""
    for customer in all_customers():
        result = engine.recommend(customer)
        affordable = destinations[
            (destinations[config.COL_CATEGORY] == customer.category)
            & (destinations[config.COL_PRICE] <= customer.budget)
        ]
        assert len(result.recommendations) == min(config.TOP_N, len(affordable))
        assert {r.name for r in result.recommendations} <= set(affordable[config.COL_NAME])


def test_no_result_shows_cheapest_as_information_only(engine, destinations):
    customer = CustomerProfile(budget=100, days=5, category="Natuur", companion="Gezin")
    result = engine.recommend(customer)
    cheapest = destinations[destinations[config.COL_CATEGORY] == "Natuur"][config.COL_PRICE].min()

    assert not result.has_results
    assert result.cheapest_in_category["price"] == cheapest
    assert result.cheapest_in_category["price"] > customer.budget


def test_cheapest_not_filled_when_there_are_results(engine):
    result = engine.recommend(CustomerProfile(budget=5000, days=7, category="Stad", companion="Stel"))
    assert result.has_results
    assert result.cheapest_in_category is None


def test_customer_vector_matches_training_columns(destinations):
    """A single customer row must get exactly the same columns as the destinations."""
    prep = FeaturePreprocessor().fit(destinations)
    customer = prep.transform_customer(CustomerProfile(2000, 7, "Strand", "Gezin"))
    assert list(customer.columns) == list(prep.transform_destinations(destinations).columns)
    assert customer.shape == (1, 9)
    assert customer.filter(like="soort_").sum(axis=1).iloc[0] == 1.0


def test_scaler_fitted_on_destinations_only(destinations):
    prep = FeaturePreprocessor().fit(destinations)
    mean_before = prep.scaler.mean_.copy()
    prep.transform_customer(CustomerProfile(999999, 99, "Stad", "Alleen"))
    assert (prep.scaler.mean_ == mean_before).all()


def test_model_b_ignores_price(destinations):
    prep = FeaturePreprocessor(use_price=False).fit(destinations)
    assert (prep.transform_destinations(destinations)[config.COL_PRICE] == 0).all()


@pytest.mark.parametrize(
    "budget, days, category, companion",
    [(0, 7, "Strand", "Stel"), (-50, 7, "Strand", "Stel"), (1000, 0, "Strand", "Stel"),
     (1000, 2.5, "Strand", "Stel"), (1000, 7, "Berg", "Stel"), (1000, 7, "Strand", "Collega's")],
)
def test_invalid_preferences_rejected(budget, days, category, companion):
    with pytest.raises(InvalidPreferencesError):
        validate_preferences(budget, days, category, companion)


def test_explanations_reflect_real_values(engine):
    customer = CustomerProfile(budget=3000, days=9, category="Strand", companion="Stel")
    for rec in engine.recommend(customer).recommendations:
        for lang in LANGUAGES:
            text = " ".join(render_explanation(rec.reasons, lang))
            assert str(rec.days) in text
        codes = {r.code for r in rec.reasons}
        assert ("companion_match" in codes) == (rec.companion == customer.companion)
