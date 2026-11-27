"""Language understanding: intent model quality, wish extraction (FR-02, FR-04) and privacy (FR-19)."""

import pytest

from src.nlu.intent_classifier import train_and_evaluate
from src.nlu.privacy import check_privacy
from src.nlu.slots import extract_slots
from src.nlu.understanding import Understander


def test_intent_model_beats_chance_by_far():
    e = train_and_evaluate()
    assert e.accuracy >= 0.6           # 13 classes: chance is ± 0.08
    assert e.matrix.to_numpy().sum() == e.n_test


@pytest.fixture(scope="module")
def nlu():
    return Understander()


@pytest.mark.parametrize("text, intent", [
    ("ik wil deze tour boeken", "boeken"), ("kan je mijn reservering annuleren", "boeken"),
    ("ik wil een medewerker spreken", "medewerker"), ("opnieuw", "opnieuw"),
    ("binnenland, 3 dagen, met z'n tweeën, 400 euro", "voorkeur"),
])
def test_safety_rules(nlu, text, intent):
    assert nlu.understand(text).intent == intent


def test_gibberish_is_not_understood(nlu):
    assert not nlu.understand("qwxzpl vbnmk").understood


@pytest.mark.parametrize("text, expected", [
    ("2 dagen jungle met mn vrouw, max 300 euro", {"tour_type": "Binnenland & natuur", "companion": "Stel", "days": 2, "budget": 300}),
    ("we zijn met z'n vijven, rondreis, 2000 in totaal", {"tour_type": "Rondreis", "travelers": 5, "budget": 2000, "budget_is_total": True}),
    ("stadstour van een paar uur, 50 euro", {"tour_type": "Stad & omgeving", "days": 0.5, "budget": 50}),
    ("met 2 kinderen naar peperpot", {"companion": "Gezin", "travelers": 4}),
    ("toch liever een week", {"days": 7}),
])
def test_slots(text, expected):
    slots = extract_slots(text)
    for key, value in expected.items():
        assert getattr(slots, key) == value, key


@pytest.mark.parametrize("text, kind", [
    ("mail me op jan@voorbeeld.sr", "e-mailadres"), ("bel +597 8123456", "telefoonnummer"),
    ("mijn kaart is 4111 1111 1111 1111", "creditcardnummer"), ("ik heet Jan Pinas", "naam"),
    ("ik woon op Kernkampweg 12", "adres"),
])
def test_fr19_personal_data_detected_and_removed(text, kind):
    check = check_privacy(text)
    assert kind in check.found and "[verwijderd]" in check.clean_text


def test_budgets_are_not_mistaken_for_personal_data():
    assert not check_privacy("budget 8500 voor 4 dagen met 2 kinderen").has_personal_data
