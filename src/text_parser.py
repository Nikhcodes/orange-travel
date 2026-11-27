"""Understand a free-text travel wish, e.g. "7 dagen strand met mijn vriendin, 1500 dollar".

This is simple keyword and number recognition (no machine learning). It only
fills in the four questions the chatbot would otherwise ask with buttons.
Anything it does not recognise, the bot simply asks for.
"""

import re
from dataclasses import dataclass, field

from src import config

CATEGORY_WORDS = {
    "Strand": ["strand", "beach", "zee", "sekanti", "zon", "eiland", "kust", "snorkel", "duik"],
    "Natuur": ["natuur", "nature", "jungle", "bos", "busi", "berg", "bergen", "regenwoud", "waterval", "safari",
               "wandel", "hike", "binnenland", "nâtur", "natur"],
    "Stad": ["stad", "city", "foto", "stedentrip", "citytrip", "shoppen", "shopping", "museum", "musea"],
}

COMPANION_WORDS = {
    "Alleen": ["alleen", "solo", "wawan", "mezelf", "in mijn eentje", "by myself", "alone"],
    "Stel": ["stel", "partner", "vriendin", "vriend ", "vrouw", "man ", "echtgeno", "koppel", "huwelijksreis",
             "honeymoon", "romantisch", "met zijn tweeën", "met z'n tweeën", "wi tu", "mi wefi", "mi masra", "couple"],
    "Gezin": ["gezin", "kinderen", "kids", "familie", "famiri", "pikin", "zoon", "dochter", "family", "kind "],
    "Vrienden": ["vrienden", "vriendengroep", "vriendinnen", "mati", "friends", "groep", "maten"],
}

TOTAL_WORDS = ["totaal", "samen", "in totaal", "voor iedereen", "voor ons allemaal", "total", "alles bij elkaar"]
PER_PERSON_WORDS = ["per persoon", "p.p.", "pp", "per person", "wan wan sma", "ieder", "elk"]
RESTART_WORDS = ["opnieuw", "reset", "begin opnieuw", "start opnieuw", "baka", "bigin baka", "restart"]

NUMBER_WORDS = {"twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10,
                "tu": 2, "dri": 3, "fo": 4, "feifi": 5, "siksi": 6}


@dataclass
class ParsedWish:
    category: str | None = None
    companion: str | None = None
    travelers: int | None = None
    days: int | None = None
    budget: float | None = None
    budget_is_total: bool = False
    restart: bool = False
    recognised: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.recognised and not self.restart


def _number(token: str) -> float | None:
    token = token.replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})+", token) else token.replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return NUMBER_WORDS.get(token)


def parse_wish(text: str) -> ParsedWish:
    """Extract category, companion, travelers, days and budget from free text."""
    wish = ParsedWish()
    lowered = f" {text.lower().strip()} "

    if any(f" {w}" in lowered for w in RESTART_WORDS) and len(lowered.split()) <= 3:
        wish.restart = True
        return wish

    for category, words in CATEGORY_WORDS.items():
        if any(w in lowered for w in words):
            wish.category = category
            wish.recognised.append("category")
            break

    for companion, words in COMPANION_WORDS.items():
        if any(w in lowered for w in words):
            wish.companion = companion
            wish.recognised.append("companion")
            break

    # Number of travelers: "4 personen", "met z'n vieren", "met 5 mensen"
    match = re.search(r"(\d+|\w+)\s*(personen|persoon|mensen|reizigers|sma|people|pers\.?)\b", lowered)
    if match and _number(match.group(1)):
        wish.travelers = int(_number(match.group(1)))
        wish.recognised.append("travelers")
    elif wish.companion == "Alleen":
        wish.travelers = 1
    elif wish.companion == "Stel":
        wish.travelers = 2

    # Days: "7 dagen", "10 days", "5 dei", "2 weken", "een week", "weekend"
    match = re.search(r"(\d+|\w+)\s*(dagen|dag|days|day|dei|nachten|nights)\b", lowered)
    if match and _number(match.group(1)):
        wish.days = int(_number(match.group(1)))
    else:
        match = re.search(r"(\d+|\w+)\s*(weken|week|wiki)\b", lowered)
        if match and _number(match.group(1)):
            wish.days = int(_number(match.group(1))) * 7
        elif re.search(r"\b(een|1|wan)\s*(week|wiki)\b", lowered):
            wish.days = 7
        elif "weekend" in lowered:
            wish.days = 3
    if wish.days:
        wish.recognised.append("days")

    # Budget: a number with $, usd or dollar, or a number of 100 or more that is not days/people.
    budget = None
    match = re.search(r"(?:\$|usd|us\$)\s*([\d.,]+)|([\d.,]+)\s*(?:\$|usd|dollar|dollars|srd)\b", lowered)
    if match:
        budget = _number(match.group(1) or match.group(2))
    else:
        for token in re.findall(r"\d[\d.,]*", lowered):
            value = _number(token)
            if value and value >= 100:
                budget = value
                break
    if budget and budget > 0:
        wish.budget = budget
        wish.budget_is_total = any(w in lowered for w in TOTAL_WORDS) and not any(w in lowered for w in PER_PERSON_WORDS)
        wish.recognised.append("budget")

    if wish.travelers is not None:
        wish.travelers = max(1, min(wish.travelers, config.MAX_TRAVELERS))
    return wish
