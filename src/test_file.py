"""Recognise a pasted or uploaded test file, whatever its exact column names or separator.

Used by the team dashboard: paste a list of wishes, the app finds out which column is the
budget, the duration, etc., cleans the values and runs the evaluation.
"""

import io
from dataclasses import dataclass, field

import pandas as pd

from src import config

COLUMN_SYNONYMS = {
    config.COL_WISH_ID: ["wens_id", "id", "nr", "nummer", "scenario", "scenario_id", "wens", "test"],
    config.COL_BUDGET: ["budget_eur", "budget", "budget (eur)", "budget_usd", "max_budget", "bedrag", "eur"],
    config.COL_WISH_DAYS: ["dagen", "days", "duur", "aantal_dagen", "aantal dagen", "dei"],
    config.COL_WISH_TYPE: ["type", "soort", "soort_reis", "soort reis", "type_reis", "reistype", "category", "categorie"],
    config.COL_WISH_COMPANION: ["gezelschap", "reisgezelschap", "companion", "met wie", "met_wie", "geschikt_voor"],
    config.COL_TRAVELERS: ["personen", "aantal_personen", "aantal personen", "reizigers", "travelers", "pax"],
    config.COL_EXPECTED: ["verwacht", "expected_best", "verwachte_tour", "verwachte tour", "beste", "expected", "beste_tour"],
    config.COL_WISH_KIND: ["soort_wens", "kind", "scenario_type"],
    config.COL_SPLIT: ["set", "split", "dataset"],
}
REQUIRED = [config.COL_BUDGET, config.COL_WISH_DAYS, config.COL_WISH_TYPE, config.COL_WISH_COMPANION]

TYPE_SYNONYMS = {
    "stad": "Stad & omgeving", "stad & omgeving": "Stad & omgeving", "city": "Stad & omgeving", "paramaribo": "Stad & omgeving",
    "binnenland": "Binnenland & natuur", "natuur": "Binnenland & natuur", "binnenland & natuur": "Binnenland & natuur",
    "jungle": "Binnenland & natuur", "nature": "Binnenland & natuur",
    "rondreis": "Rondreis", "round trip": "Rondreis", "roundtrip": "Rondreis",
}
COMPANION_SYNONYMS = {
    "alleen": "Alleen", "solo": "Alleen", "wawan": "Alleen", "stel": "Stel", "koppel": "Stel", "couple": "Stel",
    "partner": "Stel", "gezin": "Gezin", "familie": "Gezin", "family": "Gezin", "vrienden": "Vrienden",
    "friends": "Vrienden", "groep": "Vrienden",
}
NO_RESULT_WORDS = {"geen", "none", "-", "", "nan", "geen advies", "geen resultaat", "n/a"}


@dataclass
class RecognisedFile:
    data: pd.DataFrame
    mapping: dict[str, str]
    missing: list[str]
    has_expected: bool
    looks_like_tours: bool = False
    problems: list[str] = field(default_factory=list)
    skipped_rows: int = 0


def read_table(text: str | bytes) -> pd.DataFrame:
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig", errors="replace")
    return pd.read_csv(io.StringIO(text.strip()), sep=None, engine="python", dtype=str, skipinitialspace=True)


def _match_columns(columns: list[str]) -> dict[str, str]:
    normalised = {c.strip().lower().replace("-", "_"): c for c in columns}
    mapping = {}
    for ours, names in COLUMN_SYNONYMS.items():
        for name in names:
            key = name.lower().replace("-", "_")
            if key in normalised and normalised[key] not in mapping.values():
                mapping[ours] = normalised[key]
                break
    return mapping


def _to_number(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    cleaned = str(value).lower()
    for junk in ("€", "$", "eur", "usd", "dagen", "dag", "dei", "p.p.", "pp"):
        cleaned = cleaned.replace(junk, "")
    cleaned = cleaned.strip()
    if cleaned.count(".") == 1 and "," not in cleaned and len(cleaned.split(".")[1]) == 3:
        cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def recognise(raw: pd.DataFrame, tour_names: set[str]) -> RecognisedFile:
    mapping = _match_columns(list(raw.columns))
    lower = {c.strip().lower() for c in raw.columns}
    looks_like_tours = {"tour", "prijs_eur"} <= lower
    missing = [c for c in REQUIRED if c not in mapping]
    if missing:
        return RecognisedFile(pd.DataFrame(), mapping, missing, False, looks_like_tours)

    df = pd.DataFrame({ours: raw[theirs] for ours, theirs in mapping.items()})
    problems = []
    df[config.COL_BUDGET] = df[config.COL_BUDGET].map(_to_number)
    df[config.COL_WISH_DAYS] = df[config.COL_WISH_DAYS].map(_to_number)
    df[config.COL_WISH_TYPE] = df[config.COL_WISH_TYPE].map(lambda v: TYPE_SYNONYMS.get(str(v).strip().lower()))
    df[config.COL_WISH_COMPANION] = df[config.COL_WISH_COMPANION].map(lambda v: COMPANION_SYNONYMS.get(str(v).strip().lower()))
    if config.COL_TRAVELERS in df:
        df[config.COL_TRAVELERS] = df[config.COL_TRAVELERS].map(_to_number)
    else:
        df[config.COL_TRAVELERS] = df[config.COL_WISH_COMPANION].map({"Alleen": 1, "Stel": 2}).fillna(2)
    df[config.COL_TRAVELERS] = df[config.COL_TRAVELERS].fillna(2)
    if config.COL_WISH_ID not in df:
        df[config.COL_WISH_ID] = [f"R{i + 1:02d}" for i in range(len(df))]

    has_expected = config.COL_EXPECTED in df
    if has_expected:
        lookup = {name.lower(): name for name in tour_names}

        def clean(v):
            text = "" if v is None or pd.isna(v) else str(v).strip()
            return config.NO_RESULT_LABEL if text.lower() in NO_RESULT_WORDS else lookup.get(text.lower(), text)

        df[config.COL_EXPECTED] = df[config.COL_EXPECTED].map(clean)
        unknown = sorted(set(df[config.COL_EXPECTED]) - tour_names - {config.NO_RESULT_LABEL})
        if unknown:
            problems.append(f"Onbekende verwachte tour(s): {', '.join(unknown)}")
    for col, default in ((config.COL_WISH_KIND, "onbekend"), (config.COL_SPLIT, "-")):
        if col not in df:
            df[col] = default

    valid = (df[config.COL_BUDGET].notna() & (df[config.COL_BUDGET] > 0) & df[config.COL_WISH_DAYS].notna()
             & (df[config.COL_WISH_DAYS] > 0) & df[config.COL_WISH_TYPE].notna() & df[config.COL_WISH_COMPANION].notna()
             & (df[config.COL_TRAVELERS] >= 1))
    skipped = int((~valid).sum())
    if skipped:
        bad = df.loc[~valid, config.COL_WISH_ID].astype(str).tolist()
        problems.append(f"{skipped} rij(en) overgeslagen door ongeldige waarden: {', '.join(bad[:10])}")
    df = df[valid].copy()
    df[config.COL_TRAVELERS] = df[config.COL_TRAVELERS].astype(int)
    return RecognisedFile(df.reset_index(drop=True), mapping, [], has_expected, looks_like_tours, problems, skipped)
