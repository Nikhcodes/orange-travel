"""Business rules of the recommender (FR-07 .. FR-12) and the feature pipeline."""

import itertools

import pytest

from src import config
from src.preprocessing import CustomerProfile, FeaturePreprocessor
from src.recommendation_engine import InvalidPreferencesError, RecommendationEngine, validate_preferences

BUDGETS = [10, 27.5, 50, 95, 180, 400, 900, 1500, 2500]
DAYS = [0.5, 1, 2.5, 4.5, 7, 16]


def customers():
    for b, d, t, c in itertools.product(BUDGETS, DAYS, config.TYPES, config.COMPANIONS):
        yield CustomerProfile(b, d, t, c, {"Alleen": 1, "Stel": 2}.get(c, 4))


@pytest.fixture(scope="module", params=[None, {}, {"prijs": 0.0}], ids=["eindmodel", "model_A", "model_B"])
def engine(request, tours):
    return RecommendationEngine(tours, weights=request.param)


def test_fr12_advice_never_above_budget(engine):
    """648 wishes x 3 models: an ADVISED tour is never more expensive than the budget."""
    for customer in customers():
        for rec in engine.recommend(customer).recommendations:
            assert rec.price <= customer.budget


def test_never_invents_or_misses_tours(engine, tours):
    for customer in customers():
        result = engine.recommend(customer)
        affordable = tours[tours[config.COL_PRICE] <= customer.budget]
        assert len(result.recommendations) == min(config.TOP_N, len(affordable))
        assert {r.name for r in result.recommendations} <= set(affordable[config.COL_NAME])


def test_fr12_cheapest_options_only_when_nothing_fits(engine, tours):
    result = engine.recommend(CustomerProfile(10, 1, "Binnenland & natuur", "Gezin", 4))
    assert not result.has_results
    assert 1 <= len(result.over_budget) <= config.TOP_N
    assert all(not r.within_budget and any(x.code == "budget_over" for x in r.reasons) for r in result.over_budget)
    same_type = tours[tours[config.COL_TYPE] == "Binnenland & natuur"]
    assert result.over_budget[0].price == same_type[config.COL_PRICE].min()
    assert engine.recommend(CustomerProfile(2000, 7, "Rondreis", "Stel", 2)).over_budget == []


def test_fr09_every_advice_has_price_specs_and_reasons(engine):
    for rec in engine.recommend(CustomerProfile(400, 2.5, "Binnenland & natuur", "Stel", 2)).recommendations:
        assert rec.price > 0 and rec.duration_text and rec.url.startswith("https://www.orangesuriname.com/")
        assert {r.code.split("_")[0] for r in rec.reasons} >= {"budget", "duration", "type", "companion"}


def test_fr11_mismatch_is_reported(tours):
    engine = RecommendationEngine(tours)
    result = engine.recommend(CustomerProfile(300, 16, "Rondreis", "Gezin", 4))   # no round trip under €845
    assert result.has_results
    assert any(not r.positive and r.code == "type_other" for rec in result.recommendations for r in rec.reasons)
    assert not result.recommendations[0].fully_matches


def test_fr08_only_tours_in_suriname_from_orange_travel(tours):
    assert tours[config.COL_URL].str.startswith("https://www.orangesuriname.com/").all()
    names = " ".join(tours[config.COL_NAME]).lower()
    assert "guyana" not in names and "guiana" not in names


def test_customer_vector_matches_tour_columns(tours):
    prep = FeaturePreprocessor().fit(tours)
    customer = prep.transform_customer(CustomerProfile(200, 2, "Stad & omgeving", "Gezin", 4))
    assert list(customer.columns) == list(prep.transform_tours(tours).columns)
    assert customer.shape == (1, 9)


def test_scaler_fitted_on_tours_only(tours):
    prep = FeaturePreprocessor().fit(tours)
    before = prep.scaler.mean_.copy()
    prep.transform_customer(CustomerProfile(99999, 60, "Rondreis", "Alleen", 1))
    assert (prep.scaler.mean_ == before).all()


@pytest.mark.parametrize("args", [(0, 1, "Rondreis", "Stel"), (-5, 1, "Rondreis", "Stel"), (100, 0, "Rondreis", "Stel"),
                                  (100, 1, "Strand", "Stel"), (100, 1, "Rondreis", "Collega's"), (100, 1, "Rondreis", "Gezin", 0)])
def test_invalid_wishes_rejected(args):
    with pytest.raises(InvalidPreferencesError):
        validate_preferences(*args)
