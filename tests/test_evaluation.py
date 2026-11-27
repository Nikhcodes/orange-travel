"""Tests for the evaluation, the rubric labels and the tuning protocol."""

import pandas as pd
import pytest

from src import config
from src.data_loader import load_destinations, load_test_customers
from src.evaluation import companion_matrix, evaluate_scenarios, relevance_matrix, summarize
from src.experiments import best_weights, split, tune_weights
from src.recommendation_engine import RecommendationEngine
from src.rubric import rubric_best


@pytest.fixture(scope="module")
def destinations() -> pd.DataFrame:
    return load_destinations()


@pytest.fixture(scope="module")
def scenarios(destinations) -> pd.DataFrame:
    return load_test_customers(destinations=destinations)


def test_split_is_balanced(scenarios):
    assert (scenarios[config.COL_SPLIT] == config.SPLIT_DEV).sum() == 30
    assert (scenarios[config.COL_SPLIT] == config.SPLIT_TEST).sum() == 30


def test_labels_follow_rubric(destinations, scenarios):
    for _, row in scenarios.iterrows():
        expected = rubric_best(destinations, row[config.COL_BUDGET], row[config.COL_WISH_DAYS],
                               row[config.COL_WISH_CATEGORY], row[config.COL_WISH_COMPANION])
        assert expected == row[config.COL_EXPECTED], row[config.COL_SCENARIO_ID]


def test_final_weights_are_the_tuning_result(destinations, scenarios):
    """The weights in config must be exactly what tuning on the DEVELOPMENT set chose."""
    table = tune_weights(destinations, split(scenarios, config.SPLIT_DEV))
    chosen = best_weights(table)
    assert {k: config.FINAL_WEIGHTS[k] for k in chosen} == chosen


def test_success_criteria_on_test_set(destinations, scenarios):
    results = evaluate_scenarios(RecommendationEngine(destinations), split(scenarios, config.SPLIT_TEST))
    summary = summarize(results)
    assert summary.budget_compliance == 1.0
    assert summary.category_match >= 0.9
    assert summary.top3_hits >= 24


def test_confusion_matrices_are_consistent(destinations, scenarios):
    results = evaluate_scenarios(RecommendationEngine(destinations), scenarios)
    matrix = relevance_matrix(results, destinations)
    assert matrix.tp + matrix.fp == results["n_recommended"].sum()
    assert matrix.tp + matrix.fp + matrix.fn + matrix.tn == len(results) * len(destinations)
    assert 0 <= matrix.precision <= 1 and 0 <= matrix.recall <= 1
    assert companion_matrix(results, destinations).to_numpy().sum() == (results["n_recommended"] > 0).sum()
