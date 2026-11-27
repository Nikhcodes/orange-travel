"""Evaluation honesty: rubric labels, tuning protocol and the assignment's success criteria."""

from src import config
from src.evaluation import evaluate_wishes, relevance_matrix, summarize
from src.experiments import best_weights, split, tune_weights
from src.recommendation_engine import RecommendationEngine
from src.rubric import rubric_best


def test_split_is_30_30(wishes):
    assert (wishes[config.COL_SPLIT] == config.SPLIT_DEV).sum() == 30
    assert (wishes[config.COL_SPLIT] == config.SPLIT_TEST).sum() == 30


def test_fr07_labels_follow_the_rubric(tours, wishes):
    for _, w in wishes.iterrows():
        assert rubric_best(tours, w[config.COL_BUDGET], w[config.COL_WISH_DAYS], w[config.COL_WISH_TYPE],
                           w[config.COL_WISH_COMPANION]) == w[config.COL_EXPECTED], w[config.COL_WISH_ID]


def test_final_weights_are_the_tuning_result(tours, wishes):
    chosen = best_weights(tune_weights(tours, split(wishes, config.SPLIT_DEV)))
    assert {k: config.FINAL_WEIGHTS[k] for k in chosen} == chosen


def test_success_criteria_on_test_set(tours, wishes):
    s = summarize(evaluate_wishes(RecommendationEngine(tours), split(wishes, config.SPLIT_TEST)))
    assert s.budget_compliance == 1.0
    assert s.type_match >= 0.9
    assert s.top3_hits >= 24


def test_confusion_matrix_adds_up(tours, wishes):
    results = evaluate_wishes(RecommendationEngine(tours), wishes)
    m = relevance_matrix(results, tours)
    assert m.tp + m.fp == results["n_aanbevolen"].sum()
    assert m.tp + m.fp + m.fn + m.tn == len(results) * len(tours)
