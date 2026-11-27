"""Create data/test_customers.csv: 60 fictional customer wishes with rubric labels.

Run from the project root:
    uv run python -m scripts.build_test_scenarios

- The wishes are generated with a FIXED random seed, so everyone gets exactly
  the same file (reproducible).
- The expected best destination comes from the written rubric (src/rubric.py),
  never from the KNN model.
- The wishes are split 50/50: 'ontwikkel' (used to tune the model) and 'test'
  (only used for the final measurement). This prevents us from tuning the
  model on the same data we report on (overfitting).

Only re-run this script if you deliberately want new test wishes. Changing the
labels after looking at the model results is NOT allowed.
"""

import numpy as np
import pandas as pd

from src import config
from src.data_loader import load_destinations
from src.rubric import explain_rubric

SEED = 2026
N_PER_SET = 30
NO_RESULT_PER_SET = 3


def generate_wishes(destinations: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    wishes = []
    cheapest = destinations.groupby(config.COL_CATEGORY)[config.COL_PRICE].min()

    for split in (config.SPLIT_DEV, config.SPLIT_TEST):
        # A few wishes with a budget below the cheapest trip in that category.
        for _ in range(NO_RESULT_PER_SET):
            category = str(rng.choice(config.CATEGORIES))
            wishes.append({
                config.COL_BUDGET: int(rng.integers(2, cheapest[category] // 50) * 50),
                config.COL_WISH_DAYS: int(rng.integers(3, 11)),
                config.COL_WISH_CATEGORY: category,
                config.COL_WISH_COMPANION: str(rng.choice(config.COMPANIONS)),
                config.COL_SPLIT: split,
            })
        # Normal wishes: budgets between $500 and $5,000, days between 3 and 14.
        for i in range(N_PER_SET - NO_RESULT_PER_SET):
            wishes.append({
                config.COL_BUDGET: int(rng.integers(10, 101) * 50),
                config.COL_WISH_DAYS: int(rng.integers(3, 15)),
                config.COL_WISH_CATEGORY: config.CATEGORIES[i % 3],
                config.COL_WISH_COMPANION: str(rng.choice(config.COMPANIONS)),
                config.COL_SPLIT: split,
            })
    return wishes


def main() -> None:
    destinations = load_destinations()
    rng = np.random.default_rng(SEED)
    wishes = generate_wishes(destinations, rng)

    rows = []
    for number, wish in enumerate(wishes, start=1):
        expected, scenario_type, motivation = explain_rubric(
            destinations, wish[config.COL_BUDGET], wish[config.COL_WISH_DAYS],
            wish[config.COL_WISH_CATEGORY], wish[config.COL_WISH_COMPANION],
        )
        rows.append({
            config.COL_SCENARIO_ID: f"T{number:02d}",
            **{k: wish[k] for k in (config.COL_BUDGET, config.COL_WISH_DAYS, config.COL_WISH_CATEGORY, config.COL_WISH_COMPANION)},
            config.COL_SCENARIO_TYPE: scenario_type,
            config.COL_EXPECTED: expected,
            config.COL_MOTIVATION: motivation,
            config.COL_SPLIT: wish[config.COL_SPLIT],
        })

    df = pd.DataFrame(rows, columns=config.SCENARIO_COLUMNS)
    df.to_csv(config.TEST_CUSTOMERS_CSV, index=False)
    print(f"{len(df)} wensen geschreven naar {config.TEST_CUSTOMERS_CSV}")
    print(pd.crosstab(df[config.COL_SCENARIO_TYPE], df[config.COL_SPLIT], margins=True))


if __name__ == "__main__":
    main()
