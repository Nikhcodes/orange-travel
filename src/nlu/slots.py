"""Extract travel wishes from free text (FR-02, FR-04).

Simple, transparent keyword and number recognition. It fills in the same four
questions the bot otherwise asks with buttons. Anything not recognised is asked for.
"""

import re
from dataclasses import dataclass, field

from src import config

TYPE_WORDS = {
    "Rondreis": ["rondreis", "rondreizen", "round trip", "roundtrip", "heel suriname", "rondtrip", "hele land"],
    "Binnenland & natuur": ["binnenland", "jungle", "natuur", "nature", "busi", "regenwoud", "rainforest", "waterval",
                            "brownsberg", "stuwmeer", "lodge", "expeditie", "berg", "galibi", "brokopondo", "awarradam",
                            "dieren", "wildlife"],
    "Stad & omgeving": ["stad", "city", "paramaribo", "foto", "commewijne", "plantage", "peperpot", "dolfijn",
                        "rivier", "stadstour", "citytour", "in de buurt"],
}
COMPANION_WORDS = {
    "Gezin": ["gezin", "kinderen", "kind ", "kids", "familie", "famiri", "pikin", "zoon", "dochter", "family", "ouders"],
    "Vrienden": ["vrienden", "vriendinnen", "vriendengroep", "mati", "friends", "groep", "maten", "collega"],
    "Stel": ["vriendin", "vriend ", "partner", "vrouw", "man ", "mijn man", "echtgeno", "koppel", "met z'n tweeën",
             "met zijn tweeën", "met zn tweeen", "huwelijksreis", "honeymoon", "couple", "wefi", "masra", "lobi"],
    "Alleen": ["alleen", "solo", "wawan", "in mijn eentje", "by myself", "alone", "single"],
}
NUMBER_WORDS = {"een": 1, "één": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7, "acht": 8,
                "negen": 9, "tien": 10, "tweeën": 2, "drieën": 3, "vieren": 4, "vijven": 5, "zessen": 6, "zevenen": 7,
                "achten": 8, "wan": 1, "tu": 2, "dri": 3, "fo": 4, "feifi": 5}
TOTAL_WORDS = ["totaal", "in totaal", "samen", "voor iedereen", "alles bij elkaar", "total", "voor ons allemaal"]
PER_PERSON_WORDS = ["per persoon", "p.p", "pp", "per person", "wan wan sma", "per stuk", "ieder"]


@dataclass
class Slots:
    tour_type: str | None = None
    companion: str | None = None
    travelers: int | None = None
    days: float | None = None
    budget: float | None = None
    budget_is_total: bool = False
    foreign_currency: bool = False
    found: list[str] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(self.found)


def _number(token: str) -> float | None:
    token = token.strip().lower()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", token):      # 1.500 or 1.500,50
        token = token.replace(".", "").replace(",", ".")
    else:
        token = token.replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return NUMBER_WORDS.get(token)


def extract_slots(text: str) -> Slots:
    slots = Slots()
    low = f" {text.lower().strip()} "

    for tour_type, words in TYPE_WORDS.items():
        if any(w in low for w in words):
            slots.tour_type = tour_type
            slots.found.append("type")
            break

    for companion, words in COMPANION_WORDS.items():
        if any(w in low for w in words):
            slots.companion = companion
            slots.found.append("companion")
            break

    m = re.search(r"(\d+|[a-zë]+)\s*(personen|persoon|mensen|reizigers|sma|people|pers\b)", low) \
        or re.search(r"met (?:z'n|zijn|zn) (\w+)", low) or re.search(r"groep van (\d+|\w+)", low)
    if m and _number(m.group(1)) and _number(m.group(1)) >= 1:
        slots.travelers = int(_number(m.group(1)))
        slots.found.append("travelers")
    elif re.search(r"(\d+|\w+)\s*(vrienden|vriendinnen|mati|maten|collega's)", low) and \
            _number(re.search(r"(\d+|\w+)\s*(vrienden|vriendinnen|mati|maten|collega's)", low).group(1)):
        friends = _number(re.search(r"(\d+|\w+)\s*(vrienden|vriendinnen|mati|maten|collega's)", low).group(1))
        slots.travelers = int(friends) + 1          # "met 6 vrienden" = 6 friends + me
        slots.found.append("travelers")
    else:
        kids = re.search(r"(\d+|\w+)\s*(kinderen|kids|kinderen)", low)
        if kids and _number(kids.group(1)):
            slots.travelers = int(_number(kids.group(1))) + 2
            slots.found.append("travelers")
    if slots.travelers is None and slots.companion == "Alleen":
        slots.travelers = 1
    if slots.travelers is None and slots.companion == "Stel":
        slots.travelers = 2

    # Duration
    days = None
    m = re.search(r"(\d+(?:[.,]\d+)?|\w+)\s*(?:dagen|dag|days|day|dei|nachten|nights)\b", low)
    if m and _number(m.group(1)):
        days = _number(m.group(1))
    elif re.search(r"(\d+|\w+)\s*(?:weken|wiki)\b", low) and _number(re.search(r"(\d+|\w+)\s*(?:weken|wiki)\b", low).group(1)):
        days = _number(re.search(r"(\d+|\w+)\s*(?:weken|wiki)\b", low).group(1)) * 7
    elif re.search(r"\b(een|1|wan)?\s*week\b", low):
        days = 7
    elif "weekend" in low or "wikènde" in low:
        days = 2.5
    elif re.search(r"(paar uur|uurtje|halve dag|dagdeel|middagje|ochtend|avondje|\d+\s*uur)", low):
        days = 0.5
    elif re.search(r"(dagtrip|dagtour|daytrip|day trip|hele dag|een dag)", low):
        days = 1
    if days:
        slots.days = float(days)
        slots.found.append("days")

    # Budget: a number with a currency, or "budget ... N", or a lone number >= 20 not used for days/people.
    m = re.search(r"(?:€|eur|euro|\$|usd|us\$|srd)\s*([\d.,]+)|([\d.,]+)\s*(?:€|euro|eur|\$|dollar|dollars|usd|srd)\b", low)
    budget = None
    if m:
        budget = _number(m.group(1) or m.group(2))
        slots.foreign_currency = bool(re.search(r"\$|usd|dollar|srd", m.group(0)))
    else:
        m = re.search(r"(?:budget|max(?:imaal)?|onder de|tot|rond de|ongeveer)\D{0,12}([\d.,]+)", low)
        if m:
            budget = _number(m.group(1))
        else:
            used = {str(int(slots.days)) if slots.days and slots.days >= 1 else None, str(slots.travelers) if slots.travelers else None}
            for token in re.findall(r"\d[\d.,]*", low):
                value = _number(token)
                if value and value >= 20 and token not in used:
                    budget = value
                    break
    if budget and budget > 0:
        slots.budget = float(budget)
        slots.budget_is_total = any(w in low for w in TOTAL_WORDS) and not any(w in low for w in PER_PERSON_WORDS)
        slots.found.append("budget")
    return slots
