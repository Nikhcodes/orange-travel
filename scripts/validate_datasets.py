"""Validate both datasets and cross-check the expected labels against the rubric.

Run from the project root:
    python -m scripts.validate_datasets

The rubric (src/rubric.py) is a written, human-style decision rule. It does NOT use
KNN, scaling or any distance: it only exists to check that every
`expected_best` in test_customers.csv follows the rules we documented.
"""

import sys

import pandas as pd

from src import config
from src.data_loader import DatasetError, load_destinations, load_test_customers
from src.rubric import rubric_best


def print_distribution(destinations: pd.DataFrame) -> None:
    """Print how destinations are spread over categories and companions."""
    print("\nVerdeling bestemmingen (soort x geschikt_voor):")
    print(pd.crosstab(destinations[config.COL_CATEGORY], destinations[config.COL_COMPANION], margins=True))
    print("\nPrijs per soort (USD):")
    print(destinations.groupby(config.COL_CATEGORY)[config.COL_PRICE].agg(["min", "median", "max"]))


def main() -> int:
    try:
        destinations = load_destinations()
        scenarios = load_test_customers(destinations=destinations)
    except DatasetError as exc:
        print(f"FOUT: {exc}")
        return 1

    print(f"OK  destinations.csv   — {len(destinations)} bestemmingen")
    print(f"OK  test_customers.csv — {len(scenarios)} scenario's")
    print_distribution(destinations)

    mismatches = []
    for _, row in scenarios.iterrows():
        expected_by_rubric = rubric_best(
            destinations, row[config.COL_BUDGET], row[config.COL_WISH_DAYS],
            row[config.COL_WISH_CATEGORY], row[config.COL_WISH_COMPANION],
        )
        if expected_by_rubric != row[config.COL_EXPECTED]:
            mismatches.append((row[config.COL_SCENARIO_ID], row[config.COL_EXPECTED], expected_by_rubric))

    print("\nScenario-types:", scenarios[config.COL_SCENARIO_TYPE].value_counts().to_dict())
    if mismatches:
        print("\nLET OP: labels die afwijken van de rubriek:")
        for scenario_id, label, rubric in mismatches:
            print(f"  {scenario_id}: CSV zegt '{label}', rubriek zegt '{rubric}'")
        return 1

    print("\nOK  alle expected_best-labels zijn consistent met de rubriek")
    return 0


if __name__ == "__main__":
    sys.exit(main())
