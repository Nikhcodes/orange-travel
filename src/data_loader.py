"""Loading and validating the CSV datasets.

Validation is strict on purpose: a recommender that silently works with a
broken price or an unknown category could violate the budget rule or produce
misleading explanations. Rows that cannot be repaired are rejected with a
clear error message instead of being guessed.
"""

from pathlib import Path

import pandas as pd

from src import config


class DatasetError(ValueError):
    """Raised when a dataset is missing, malformed or contains invalid values."""


def _read_csv(path: Path, required_columns: list[str]) -> pd.DataFrame:
    """Read a CSV file and check that all required columns are present."""
    if not path.exists():
        raise DatasetError(f"Bestand niet gevonden: {path}")
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DatasetError(f"Kan {path.name} niet inlezen: {exc}") from exc

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise DatasetError(f"{path.name} mist kolommen: {', '.join(missing)}")
    return df[required_columns].copy()


def _strip_text_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Remove surrounding whitespace so ' Strand' and 'Strand' are treated equally."""
    for col in columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def _check_positive_int(df: pd.DataFrame, column: str, file_name: str) -> None:
    """Convert a column to int and make sure every value is a positive whole number."""
    numeric = pd.to_numeric(df[column], errors="coerce")
    invalid = df[numeric.isna() | (numeric <= 0) | (numeric % 1 != 0)]
    if not invalid.empty:
        raise DatasetError(
            f"{file_name}: ongeldige waarde(n) in '{column}' op rij(en) "
            f"{[int(i) + 2 for i in invalid.index]} (moet een positief geheel getal zijn)"
        )
    df[column] = numeric.astype(int)


def _check_allowed(df: pd.DataFrame, column: str, allowed: list[str], file_name: str) -> None:
    """Make sure a categorical column only contains known values."""
    invalid = df[~df[column].isin(allowed)]
    if not invalid.empty:
        values = sorted(set(invalid[column].astype(str)))
        raise DatasetError(
            f"{file_name}: onbekende waarde(n) in '{column}': {values}. Toegestaan: {allowed}"
        )


def validate_destinations(df: pd.DataFrame, source: str = "destinations.csv") -> pd.DataFrame:
    """Validate a destination table (from a CSV file or from the admin editor).

    Checks:
        - all required columns exist
        - no empty required values
        - price and days are positive integers
        - category and companion are known values
        - ids and destination names are unique
        - at least MIN_DESTINATIONS rows
    Optional columns (beschrijving, afbeelding) are added as empty text if missing.
    """
    missing = [col for col in config.DESTINATION_COLUMNS if col not in df.columns]
    if missing:
        raise DatasetError(f"{source} mist kolommen: {', '.join(missing)}")

    df = df.copy()
    for col in config.OPTIONAL_DESTINATION_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[config.DESTINATION_COLUMNS + config.OPTIONAL_DESTINATION_COLUMNS]
    df[config.OPTIONAL_DESTINATION_COLUMNS] = df[config.OPTIONAL_DESTINATION_COLUMNS].fillna("")
    df = _strip_text_columns(
        df, [config.COL_ID, config.COL_NAME, config.COL_CATEGORY, config.COL_COMPANION, *config.OPTIONAL_DESTINATION_COLUMNS]
    )
    df[config.OPTIONAL_DESTINATION_COLUMNS] = df[config.OPTIONAL_DESTINATION_COLUMNS].fillna("")

    required = df[config.DESTINATION_COLUMNS]
    empty = required.isna() | (required.astype("string").apply(lambda c: c.str.strip()) == "")
    if empty.any().any():
        rows = [int(i) + 2 for i in df[empty.any(axis=1)].index]
        raise DatasetError(f"{source}: lege waarden op rij(en) {rows}")

    _check_positive_int(df, config.COL_PRICE, source)
    _check_positive_int(df, config.COL_DAYS, source)
    _check_allowed(df, config.COL_CATEGORY, config.CATEGORIES, source)
    _check_allowed(df, config.COL_COMPANION, config.COMPANIONS, source)

    for col in (config.COL_ID, config.COL_NAME):
        duplicates = df[df[col].duplicated()][col].tolist()
        if duplicates:
            raise DatasetError(f"{source}: dubbele waarde(n) in '{col}': {duplicates}")

    if len(df) < config.MIN_DESTINATIONS:
        raise DatasetError(f"{source}: {len(df)} bestemmingen, minimaal {config.MIN_DESTINATIONS} vereist")
    return df.reset_index(drop=True)


def load_destinations(path: Path = config.DESTINATIONS_CSV) -> pd.DataFrame:
    """Load and validate the destination dataset."""
    if not path.exists():
        raise DatasetError(f"Bestand niet gevonden: {path}")
    try:
        df = pd.read_csv(path, encoding="utf-8", dtype={config.COL_IMAGE: "string", config.COL_DESCRIPTION: "string"})
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DatasetError(f"Kan {path.name} niet inlezen: {exc}") from exc
    return validate_destinations(df, path.name)


def load_test_customers(
    path: Path = config.TEST_CUSTOMERS_CSV,
    destinations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Load and validate the test scenarios.

    If ``destinations`` is given, every ``expected_best`` must be either an
    existing destination name or the NO_RESULT_LABEL.
    """
    df = _read_csv(path, config.SCENARIO_COLUMNS)
    df = _strip_text_columns(
        df,
        [config.COL_SCENARIO_ID, config.COL_WISH_CATEGORY, config.COL_WISH_COMPANION,
         config.COL_SCENARIO_TYPE, config.COL_EXPECTED, config.COL_MOTIVATION, config.COL_SPLIT],
    )

    if df.isna().any().any():
        rows = [int(i) + 2 for i in df[df.isna().any(axis=1)].index]
        raise DatasetError(f"{path.name}: lege waarden op rij(en) {rows}")

    _check_positive_int(df, config.COL_BUDGET, path.name)
    _check_positive_int(df, config.COL_WISH_DAYS, path.name)
    _check_allowed(df, config.COL_WISH_CATEGORY, config.CATEGORIES, path.name)
    _check_allowed(df, config.COL_WISH_COMPANION, config.COMPANIONS, path.name)

    unknown_split = sorted(set(df[config.COL_SPLIT]) - {config.SPLIT_DEV, config.SPLIT_TEST})
    if unknown_split:
        raise DatasetError(f"{path.name}: onbekende waarde(n) in 'set': {unknown_split}")

    duplicates = df[df[config.COL_SCENARIO_ID].duplicated()][config.COL_SCENARIO_ID].tolist()
    if duplicates:
        raise DatasetError(f"{path.name}: dubbele scenario_id's: {duplicates}")

    if destinations is not None:
        valid_labels = set(destinations[config.COL_NAME]) | {config.NO_RESULT_LABEL}
        unknown = sorted(set(df[config.COL_EXPECTED]) - valid_labels)
        if unknown:
            raise DatasetError(f"{path.name}: expected_best verwijst naar onbekende bestemming(en): {unknown}")

    if len(df) < config.MIN_SCENARIOS:
        raise DatasetError(f"{path.name}: {len(df)} scenario's, minimaal {config.MIN_SCENARIOS} vereist")
    return df.reset_index(drop=True)
