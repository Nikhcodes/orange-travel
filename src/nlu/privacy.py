"""Detect and remove personal data before anything is processed (FR-19, NFR-07).

The bot never needs personal data. When a message contains something that looks
like it, the bot warns the customer and works only with the cleaned text.
Nothing is stored: the API keeps no message history.
"""

import re
from dataclasses import dataclass

PLACEHOLDER = "[verwijderd]"

PATTERNS = {
    "e-mailadres": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}\s?(?:[A-Z0-9]{4}\s?){2,7}[A-Z0-9]{1,4}\b", re.I),
    "creditcardnummer": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "telefoonnummer": re.compile(r"(?:\+|00)\d[\d\s-]{6,14}\d|\b0\d{9}\b|\b0?[678]\d{6}\b"),
    "geboortedatum": re.compile(r"\b(?:geboren|geb\.?|geboortedatum|dob)\D{0,15}\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", re.I),
    "paspoort- of ID-nummer": re.compile(r"\b(?:paspoort|passport|id[- ]?nummer|id[- ]?kaart|bsn|identiteitskaart)\w*\D{0,12}[A-Z0-9]{6,12}\b", re.I),
    "adres": re.compile(r"\b[A-Z][a-z]+(?:straat|weg|laan|plein|kade|gracht|dreef)\s+\d+[a-z]?\b"),
    "naam": re.compile(r"\b(?:mijn naam is|ik heet|my name is)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", re.I),
}


@dataclass
class PrivacyCheck:
    clean_text: str
    found: list[str]

    @property
    def has_personal_data(self) -> bool:
        return bool(self.found)


def _luhn(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def check_privacy(text: str) -> PrivacyCheck:
    found, clean = [], text
    for label, pattern in PATTERNS.items():
        def replace(match: re.Match) -> str:
            if label == "creditcardnummer" and not _luhn(match.group(0)):
                return match.group(0)
            if label not in found:
                found.append(label)
            return PLACEHOLDER
        clean = pattern.sub(replace, clean)
    return PrivacyCheck(clean, found)
