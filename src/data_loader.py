"""Loading and validating the CSV files.

Validation is strict on purpose: a recommender that silently works with a broken
price or an unknown type could break the budget rule or give misleading advice.
"""

from pathlib import Path

import pandas as pd

from src import config


class DatasetError(ValueError):
    """Raised when a dataset is missing, malformed or contains invalid values."""


def _rows(mask: pd.Series) -> list[int]:
    """Human row numbers (header = row 1)."""
    return [int(i) + 2 for i in mask[mask].index]


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DatasetError(f"Bestand niet gevonden: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8", dtype={config.COL_NOTE: "string"})
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DatasetError(f"Kan {path.name} niet inlezen: {exc}") from exc


def validate_tours(df: pd.DataFrame, source: str = "tours.csv") -> pd.DataFrame:
    """Validate a tour table (from the CSV file or from the dashboard editor)."""
    df = df.copy()
    for col in config.OPTIONAL_TOUR_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    missing = [c for c in config.TOUR_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetError(f"{source} mist kolommen: {', '.join(missing)}")
    df = df[config.TOUR_COLUMNS]
    df[config.OPTIONAL_TOUR_COLUMNS] = df[config.OPTIONAL_TOUR_COLUMNS].fillna("").astype(str)

    text_cols = [config.COL_ID, config.COL_NAME, config.COL_TYPE, config.COL_INTENSITY, config.COL_URL,
                 config.COL_DESCRIPTION, config.COL_REGION, config.COL_DURATION_TEXT]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()
    empty = df[text_cols].isna() | (df[text_cols] == "")
    if empty.any().any():
        raise DatasetError(f"{source}: lege verplichte waarden op rij(en) {_rows(empty.any(axis=1))}")

    for col in (config.COL_PRICE, config.COL_DAYS_MIN, config.COL_DAYS_MAX):
        values = pd.to_numeric(df[col], errors="coerce")
        bad = values.isna() | (values <= 0)
        if bad.any():
            raise DatasetError(f"{source}: '{col}' moet een positief getal zijn (rij(en) {_rows(bad)})")
        df[col] = values.astype(float)
    if (df[config.COL_DAYS_MAX] < df[config.COL_DAYS_MIN]).any():
        raise DatasetError(f"{source}: dagen_max is kleiner dan dagen_min "
                           f"(rij(en) {_rows(df[config.COL_DAYS_MAX] < df[config.COL_DAYS_MIN])})")

    persons = pd.to_numeric(df[config.COL_MIN_PERSONS], errors="coerce")
    bad = persons.isna() | (persons < 1) | (persons % 1 != 0)
    if bad.any():
        raise DatasetError(f"{source}: 'min_personen' moet een geheel getal ≥ 1 zijn (rij(en) {_rows(bad)})")
    df[config.COL_MIN_PERSONS] = persons.astype(int)

    for col in config.COMPANION_COLUMNS.values():
        values = pd.to_numeric(df[col], errors="coerce")
        bad = ~values.isin([0, 1])
        if bad.any():
            raise DatasetError(f"{source}: '{col}' moet 0 of 1 zijn (rij(en) {_rows(bad)})")
        df[col] = values.astype(int)
    no_companion = df[list(config.COMPANION_COLUMNS.values())].sum(axis=1) == 0
    if no_companion.any():
        raise DatasetError(f"{source}: elke tour moet bij minstens één reisgezelschap passen (rij(en) {_rows(no_companion)})")

    for col, allowed in ((config.COL_TYPE, config.TYPES), (config.COL_INTENSITY, config.INTENSITIES)):
        bad = ~df[col].isin(allowed)
        if bad.any():
            raise DatasetError(f"{source}: onbekende waarde(n) in '{col}': {sorted(set(df.loc[bad, col]))}. "
                               f"Toegestaan: {allowed}")

    bad_url = ~df[config.COL_URL].str.startswith("https://www.orangesuriname.com/")
    if bad_url.any():
        raise DatasetError(f"{source}: bronlink moet naar orangesuriname.com wijzen (rij(en) {_rows(bad_url)})")

    for col in (config.COL_ID, config.COL_NAME):
        dup = df[col].duplicated()
        if dup.any():
            raise DatasetError(f"{source}: dubbele waarde(n) in '{col}': {df.loc[dup, col].tolist()}")
    if len(df) < config.MIN_TOURS:
        raise DatasetError(f"{source}: {len(df)} tours, minimaal {config.MIN_TOURS} vereist")
    return df.reset_index(drop=True)


def load_tours(path: Path = config.TOURS_CSV) -> pd.DataFrame:
    return validate_tours(_read(path), path.name)


def load_test_wishes(path: Path = config.TEST_WISHES_CSV, tours: pd.DataFrame | None = None) -> pd.DataFrame:
    """Load and validate the test wishes."""
    df = _read(path)
    missing = [c for c in config.WISH_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetError(f"{path.name} mist kolommen: {', '.join(missing)}")
    df = df[config.WISH_COLUMNS].copy()
    if df.isna().any().any():
        raise DatasetError(f"{path.name}: lege waarden op rij(en) {_rows(df.isna().any(axis=1))}")
    for col in (config.COL_BUDGET, config.COL_WISH_DAYS):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if (df[col].isna() | (df[col] <= 0)).any():
            raise DatasetError(f"{path.name}: '{col}' moet positief zijn")
    df[config.COL_TRAVELERS] = pd.to_numeric(df[config.COL_TRAVELERS], errors="coerce").astype(int)
    for col, allowed in ((config.COL_WISH_TYPE, config.TYPES), (config.COL_WISH_COMPANION, config.COMPANIONS),
                         (config.COL_SPLIT, [config.SPLIT_DEV, config.SPLIT_TEST])):
        bad = ~df[col].isin(allowed)
        if bad.any():
            raise DatasetError(f"{path.name}: onbekende waarde(n) in '{col}': {sorted(set(df.loc[bad, col]))}")
    if df[config.COL_WISH_ID].duplicated().any():
        raise DatasetError(f"{path.name}: dubbele wens_id's")
    if tours is not None:
        valid = set(tours[config.COL_NAME]) | {config.NO_RESULT_LABEL}
        unknown = sorted(set(df[config.COL_EXPECTED]) - valid)
        if unknown:
            raise DatasetError(f"{path.name}: 'verwacht' verwijst naar onbekende tour(s): {unknown}")
    if len(df) < config.MIN_WISHES:
        raise DatasetError(f"{path.name}: {len(df)} wensen, minimaal {config.MIN_WISHES} vereist")
    return df.reset_index(drop=True)
