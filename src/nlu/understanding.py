"""Combine the ML intent model with a few safety rules.

The intent classifier (machine learning) decides most cases. A small set of
high-precision keyword rules runs first for situations where a wrong guess would
be harmful or annoying: booking/cancelling (FR-17), asking for a human (FR-16),
restarting, and messages that clearly contain travel wishes (FR-04).
Both are evaluated separately in the dashboard so the difference is visible.
"""

import re
from dataclasses import dataclass

from src.nlu.intent_classifier import IntentClassifier
from src.nlu.slots import Slots, extract_slots

RULES = [
    ("opnieuw", re.compile(r"^\s*(opnieuw|reset|restart|bigin baka|begin opnieuw|start opnieuw|opnieuw beginnen)\W*$", re.I)),
    ("boeken", re.compile(r"\b(boek|boeken|reserveer|reserveren|reservering|annuleer|annuleren|annulering|omboeken|"
                          r"book|booking|cancel|aanbetaling|factuur)\w*", re.I)),
    ("medewerker", re.compile(r"\b(medewerker|reisadviseur|echte persoon|mens spreken|met een mens|terugbel|bel me|"
                              r"bel mij|human|iemand spreken)\w*", re.I)),
]
PREFERENCE_INTENTS = {"voorkeur", "groet", "buiten_scope", "over_bot"}


@dataclass
class Understanding:
    intent: str
    confidence: float
    understood: bool
    slots: Slots
    by_rule: bool = False


class Understander:
    def __init__(self, classifier: IntentClassifier | None = None):
        self.classifier = classifier or IntentClassifier.load()

    def understand(self, text: str) -> Understanding:
        slots = extract_slots(text)
        for intent, pattern in RULES:
            if pattern.search(text):
                return Understanding(intent, 1.0, True, slots, by_rule=True)
        prediction = self.classifier.predict(text)
        if not slots.any and not self.classifier.knows_any_word(text):
            # Not a single word the model has ever seen (e.g. "asdkjh"): do not guess (FR-15).
            return Understanding(prediction.intent, 0.0, False, slots)
        # A message with two or more travel wishes is a preference, whatever else it says.
        if len(slots.found) >= 2 and prediction.intent in PREFERENCE_INTENTS | {"meer_opties"}:
            return Understanding("voorkeur", max(prediction.confidence, 0.9), True, slots, by_rule=True)
        if slots.any and prediction.intent in PREFERENCE_INTENTS:
            return Understanding("voorkeur", max(prediction.confidence, 0.6), True, slots, by_rule=True)
        return Understanding(prediction.intent, prediction.confidence, prediction.understood, slots)
