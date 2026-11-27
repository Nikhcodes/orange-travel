"""Recognise a pasted or uploaded test file, whatever its exact column names or separator.

Used by the admin window: paste a list of wishes, the app finds out which
column is the budget, the days, etc., cleans the values and runs the test.
"""

import io
from dataclasses import dataclass, field

import pandas as pd

from src import config

COLUMN_SYNONYMS = {
    config.COL_SCENARIO_ID: ["scenario_id", "scenario", "id", "nr", "nummer", "test", "wens"],
    config.COL_BUDGET: ["budget_usd", "budget", "budget (usd)", "max_budget", "usd", "bedrag"],
    config.COL_WISH_DAYS: ["dagen", "days", "duur", "aantal_dagen", "aantal dagen", "dei"],
    config.COL_WISH_CATEGORY: ["soort", "soort_reis", "soort reis", "type_reis", "category", "categorie", "reistype"],
    config.COL_WISH_COMPANION: ["gezelschap", "reisgezelschap", "companion", "geschikt_voor", "met wie", "met_wie"],
    config.COL_EXPECTED: ["expected_best", "verwacht", "verwachte_bestemming", "verwachte bestemming", "beste",
                          "expected", "beste_bestemming"],
    config.COL_SCENARIO_TYPE: ["type", "scenario_type", "soort_test"],
    config.COL_SPLIT: ["set", "split", "dataset"],
}
REQUIRED = [config.COL_BUDGET, config.COL_WISH_DAYS, config.COL_WISH_CATEGORY, config.COL_WISH_COMPANION]

VALUE_SYNONYMS = {
    config.COL_WISH_CATEGORY: {"strand": "Strand", "beach": "Strand", "sekanti": "Strand",
                               "natuur": "Natuur", "nature": "Natuur", "busi": "Natuur",
                               "stad": "Stad", "city": "Stad", "foto": "Stad"},
    config.COL_WISH_COMPANION: {"alleen": "Alleen", "solo": "Alleen", "wawan": "Alleen",
                                "stel": "Stel", "koppel": "Stel", "couple": "Stel", "partner": "Stel",
                                "gezin": "Gezin", "familie": "Gezin", "famiri": "Gezin", "family": "Gezin",
                                "vrienden": "Vrienden", "friends": "Vrienden", "mati": "Vrienden"},
}
NO_RESULT_WORDS = {"geen", "none", "-", "", "nan", "geen advies", "geen resultaat", "noti", "n/a"}


@dataclass
class RecognisedFile:
    data: pd.DataFrame                       # cleaned rows that can be tested
    mapping: dict[str, str]                  # our column -> column name in the file
    missing: list[str]                       # required columns that were not found
    has_expected: bool
    looks_like_destinations: bool = False
    problems: list[str] = field(default_factory=list)
    skipped_rows: int = 0


def read_table(text: str | bytes) -> pd.DataFrame:
    """Read CSV/TSV/semicolon text; the separator is detected automatically."""
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


def _to_number(value: str) -> float | None:
    if value is None or pd.isna(value):
        return None
    cleaned = str(value).lower().replace("$", "").replace("usd", "").replace("dagen", "").replace("dei", "").strip()
    if cleaned.count(".") == 1 and cleaned.count(",") == 0 and len(cleaned.split(".")[1]) == 3:
        cleaned = cleaned.replace(".", "")          # 1.500 -> 1500 (Dutch thousands separator)
    cleaned = cleaned.replace(",", ".").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def recognise(raw: pd.DataFrame, destination_names: set[str]) -> RecognisedFile:
    """Map columns and clean values. Rows that cannot be used are counted and reported."""
    mapping = _match_columns(list(raw.columns))
    lower_cols = {c.strip().lower() for c in raw.columns}
    looks_like_destinations = {"bestemming", "prijs_usd"} <= lower_cols
    missing = [c for c in REQUIRED if c not in mapping]
    if missing:
        return RecognisedFile(pd.DataFrame(), mapping, missing, False, looks_like_destinations)

    df = pd.DataFrame({ours: raw[theirs] for ours, theirs in mapping.items()})
    problems = []
    df[config.COL_BUDGET] = df[config.COL_BUDGET].map(_to_number)
    df[config.COL_WISH_DAYS] = df[config.COL_WISH_DAYS].map(_to_number)
    for col, synonyms in VALUE_SYNONYMS.items():
        df[col] = df[col].map(lambda v: synonyms.get(str(v).strip().lower()) if v is not None else None)

    if config.COL_SCENARIO_ID not in df:
        df[config.COL_SCENARIO_ID] = [f"R{i + 1:02d}" for i in range(len(df))]
    has_expected = config.COL_EXPECTED in df
    if has_expected:
        lookup = {name.lower(): name for name in destination_names}

        def clean_expected(v):
            text = "" if v is None or pd.isna(v) else str(v).strip()
            if text.lower() in NO_RESULT_WORDS:
                return config.NO_RESULT_LABEL
            return lookup.get(text.lower(), text)

        df[config.COL_EXPECTED] = df[config.COL_EXPECTED].map(clean_expected)
        unknown = sorted(set(df[config.COL_EXPECTED]) - destination_names - {config.NO_RESULT_LABEL})
        if unknown:
            problems.append(f"Onbekende verwachte bestemming(en): {', '.join(unknown)}")
    if config.COL_SCENARIO_TYPE not in df:
        df[config.COL_SCENARIO_TYPE] = "onbekend"
    if config.COL_SPLIT not in df:
        df[config.COL_SPLIT] = "-"

    valid = (df[config.COL_BUDGET].notna() & (df[config.COL_BUDGET] > 0) & df[config.COL_WISH_DAYS].notna()
             & (df[config.COL_WISH_DAYS] >= 1) & (df[config.COL_WISH_DAYS] % 1 == 0)
             & df[config.COL_WISH_CATEGORY].notna() & df[config.COL_WISH_COMPANION].notna())
    skipped = int((~valid).sum())
    if skipped:
        bad = df.loc[~valid, config.COL_SCENARIO_ID].astype(str).tolist()
        problems.append(f"{skipped} rij(en) overgeslagen door ongeldige waarden: {', '.join(bad[:10])}")
    df = df[valid].copy()
    df[config.COL_WISH_DAYS] = df[config.COL_WISH_DAYS].astype(int)
    return RecognisedFile(df.reset_index(drop=True), mapping, [], has_expected, looks_like_destinations, problems, skipped)
