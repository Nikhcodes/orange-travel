"""Answer questions with information from the Orange Travel website, always with a source link (FR-13, FR-14).

Two sources:
1. tour facts from data/tours.csv (price, duration, minimum group size, intensity, ...)
2. general topics from data/knowledge_base.csv (contact, payment, booking, ...)

Retrieval uses TF-IDF + cosine similarity (scikit-learn). Below the threshold the bot
says it does not know (FR-15) instead of guessing (NFR-06).
"""

import difflib
import re
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src import config

SIMILARITY_THRESHOLD = 0.12

# Short names customers use for tours -> tour id
TOUR_ALIASES = {
    "laarwijk": "T01", "brokopondo day": "T02", "brokopondo dag": "T02", "maroon": "T03", "marron dagtrip": "T03",
    "drepada": "T03", "sendang": "T04", "redjo": "T04", "cooking": "T05", "koken": "T05", "nocturnal": "T06",
    "nachttour": "T06", "kayak tour": "T07", "kajak tour": "T07", "peperpot kajak": "T07", "peperpot kayak": "T07",
    "schildpad": "T08", "turtle": "T08", "braamspunt": "T08", "fishing": "T09", "vissen": "T09", "vistour": "T09",
    "bakkie": "T10", "bike": "T11", "fiets": "T11", "bustour": "T12", "bus tour": "T12", "dolfijn": "T13",
    "dolphin": "T13", "commewijne cruise": "T14", "commewijne tour": "T14", "commewijne boot": "T14",
    "brownsberg": "T15", "frederiksdorp": "T16", "myrysji": "T17", "jaw jaw": "T18", "jawjaw": "T18",
    "anaula": "T19", "maratakka": "T20", "urusji": "T21", "ston island": "T22", "raleigh": "T23",
    "voltzberg": "T23", "awarradam": "T24", "awaradam": "T24", "wonotobo": "T25", "ironman": "T26", "4x4": "T26",
    "blanche marie": "T27", "gran rio": "T28", "sintiadam": "T28", "fredberg": "T29", "coesewijne": "T30",
    "palumeu": "T31", "kasikasima": "T32", "kabalebo": "T33", "family roundtrip": "T34", "gezinsrondreis": "T34",
    "group round": "T35", "groepsrondreis": "T35", "adventurous trek": "T36", "9 days": "T37", "9 dagen": "T37",
    "best of suriname": "T38", "highlights": "T39", "cross country": "T40", "individual round": "T41",
    "solo traveler": "T42",
}


@dataclass
class Answer:
    text: str
    source_url: str | None
    tour_id: str | None
    score: float

    @property
    def found(self) -> bool:
        return self.source_url is not None


def find_tour(text: str, tours: pd.DataFrame) -> str | None:
    """Detect which tour a message is about (alias, exact name or fuzzy match)."""
    low = text.lower()
    # Longest alias first so "brokopondo day" beats a shorter overlapping alias.
    for alias in sorted(TOUR_ALIASES, key=len, reverse=True):
        if alias in low and TOUR_ALIASES[alias] in set(tours[config.COL_ID]):
            return TOUR_ALIASES[alias]
    names = {row[config.COL_NAME].lower(): row[config.COL_ID] for _, row in tours.iterrows()}
    for name, tour_id in names.items():
        if name in low:
            return tour_id
    words = re.findall(r"[a-zà-ÿ]{5,}", low)
    for word in words:
        match = difflib.get_close_matches(word, list(TOUR_ALIASES), n=1, cutoff=0.85)
        if match:
            return TOUR_ALIASES[match[0]]
    return None


def _money(value: float) -> str:
    return f"€{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").replace(",00", "")


def tour_answer(row: pd.Series, question: str) -> str:
    """Facts about one tour, focused on what was asked. Only data we actually have."""
    q = question.lower()
    name = row[config.COL_NAME]
    facts = []
    if re.search(r"kost|prijs|hoeveel|price|euro|€|hoe duur\b|te duur", q):
        facts.append(f"**{name}** kost vanaf **{_money(row[config.COL_PRICE])} per persoon**.")
    if re.search(r"hoe lang|duurt|lang|tijd|\buur\b|dagen|duration", q):
        facts.append(f"De tour duurt **{row[config.COL_DURATION_TEXT]}**.")
    if re.search(r"minim|personen|groep|alleen|solo", q):
        facts.append(f"Het minimum is **{row[config.COL_MIN_PERSONS]} {'persoon' if row[config.COL_MIN_PERSONS] == 1 else 'personen'}**.")
    if re.search(r"zwaar|conditie|fit|intensi|lopen|ouderen|moeilijk", q):
        level = {"laag": "rustig", "gemiddeld": "gemiddeld zwaar", "hoog": "pittig: een goede conditie is aan te raden"}
        facts.append(f"De intensiteit is **{level[row[config.COL_INTENSITY]]}**.")
    if re.search(r"kind|gezin|familie", q):
        suits = "geschikt" if int(row["gezin"]) == 1 else "niet specifiek bedoeld"
        facts.append(f"Voor gezinnen is deze tour volgens onze informatie **{suits}** ({row[config.COL_SUITABILITY_SOURCE]}).")
    if re.search(r"\bwaar\b|\bligt\b|regio|locatie|vertrek", q):
        facts.append(f"De tour is in/bij **{row[config.COL_REGION]}**.")
    if facts and name not in facts[0]:
        facts.insert(0, f"Over **{name}**:")
    if not facts:
        facts.append(f"**{name}** ({row[config.COL_TYPE].lower()}, {row[config.COL_DURATION_TEXT]}, vanaf "
                     f"{_money(row[config.COL_PRICE])} p.p.): {row[config.COL_DESCRIPTION]}")
    if row[config.COL_NOTE]:
        facts.append(f"Let op: {row[config.COL_NOTE]}")
    facts.append("Details zoals wat er precies is inbegrepen staan op de tourpagina; die is leidend.")
    return " ".join(facts)


class KnowledgeBase:
    def __init__(self, tours: pd.DataFrame, path=config.KNOWLEDGE_CSV):
        self.tours = tours
        self.entries = pd.read_csv(path, encoding="utf-8")
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        corpus = (self.entries["onderwerp"] + " " + self.entries["trefwoorden"] + " " + self.entries["antwoord"]).str.lower()
        self.matrix = self.vectorizer.fit_transform(corpus)

    def answer(self, question: str) -> Answer:
        tour_id = find_tour(question, self.tours)
        if tour_id:
            row = self.tours[self.tours[config.COL_ID] == tour_id].iloc[0]
            return Answer(tour_answer(row, question), row[config.COL_URL], tour_id, 1.0)
        scores = cosine_similarity(self.vectorizer.transform([question.lower()]), self.matrix)[0]
        best = int(scores.argmax())
        if scores[best] < SIMILARITY_THRESHOLD:
            return Answer("", None, None, float(scores[best]))
        entry = self.entries.iloc[best]
        return Answer(entry["antwoord"], entry["bron"], None, float(scores[best]))
