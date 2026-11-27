"""Tests for free-text understanding (chatbot) and test-file recognition (admin window)."""

import pytest

from src import config
from src.test_file import read_table, recognise
from src.text_parser import parse_wish


@pytest.mark.parametrize("text, expected", [
    ("7 dagen strand met mijn vriendin, 1500 dollar",
     {"category": "Strand", "companion": "Stel", "travelers": 2, "days": 7, "budget": 1500}),
    ("natuur met het gezin, 4 personen, 2 weken, totaal $6.000",
     {"category": "Natuur", "companion": "Gezin", "travelers": 4, "days": 14, "budget": 6000, "budget_is_total": True}),
    ("stad alleen weekend 800", {"category": "Stad", "companion": "Alleen", "travelers": 1, "days": 3, "budget": 800}),
    ("mi wani go na sekanti nanga mi mati, 5 dei, 2000 usd",
     {"category": "Strand", "companion": "Vrienden", "days": 5, "budget": 2000}),
])
def test_parse_wish(text, expected):
    wish = parse_wish(text)
    for key, value in expected.items():
        assert getattr(wish, key) == value, key


def test_parse_restart_and_nonsense():
    assert parse_wish("opnieuw").restart
    assert parse_wish("ik wil iets leuks").is_empty


def test_recognise_messy_file():
    text = ("Budget;Days;Category;met wie;verwacht\n$1.500;7;strand;koppel;Solenta eiland\n"
            "800;5;Beach;solo;Merivo Baai\nabc;3;stad;mati;geen\n300;3;natuur;famiri;-")
    result = recognise(read_table(text), {"Solenta Eiland", "Merivo Baai"})
    assert not result.missing and result.has_expected
    assert result.skipped_rows == 1
    assert list(result.data[config.COL_BUDGET]) == [1500, 800, 300]
    assert list(result.data[config.COL_EXPECTED]) == ["Solenta Eiland", "Merivo Baai", config.NO_RESULT_LABEL]


def test_recognise_reports_missing_columns():
    result = recognise(read_table("naam,leeftijd\nA,3"), set())
    assert set(result.missing) == {config.COL_BUDGET, config.COL_WISH_DAYS, config.COL_WISH_CATEGORY, config.COL_WISH_COMPANION}
