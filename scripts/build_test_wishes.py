"""Create data/test_wishes.csv: 60 fictional customer wishes with rubric labels.

Run from the project root:   uv run python -m scripts.build_test_wishes

- Fixed random seed -> everyone gets exactly the same file.
- The expected best tour comes from the written rubric (src/rubric.py), never from the model.
- Split 30/30: 'ontwikkel' (tuning) and 'test' (final measurement only).
Do not re-run this to "improve" scores after looking at model results.
"""

import numpy as np
import pandas as pd

from src import config
from src.data_loader import load_tours
from src.rubric import explain_rubric

SEED = 597          # Suriname's country calling code
PER_SET = 30
NO_RESULT_PER_SET = 2

# Realistic budget ranges (euro per person) per chosen type of trip.
BUDGET_RANGES = {"Stad & omgeving": (30, 220), "Binnenland & natuur": (80, 1500), "Rondreis": (600, 2600)}
DAY_CHOICES = {"Stad & omgeving": [0.5, 0.5, 1, 1, 2.5], "Binnenland & natuur": [1, 2.5, 2.5, 4.5, 4.5, 7],
               "Rondreis": [7, 9, 12, 16, 16]}
TRAVELERS = {"Alleen": [1], "Stel": [2], "Gezin": [3, 4, 5], "Vrienden": [2, 3, 4, 6]}


def generate(rng: np.random.Generator) -> list[dict]:
    wishes = []
    for split in (config.SPLIT_DEV, config.SPLIT_TEST):
        for i in range(PER_SET):
            tour_type = config.TYPES[i % 3]
            companion = str(rng.choice(config.COMPANIONS))
            if i < NO_RESULT_PER_SET:
                budget = float(rng.choice([15, 20, 25]))
            else:
                low, high = BUDGET_RANGES[tour_type]
                budget = float(round(rng.uniform(low, high) / 5) * 5)
            wishes.append({
                config.COL_BUDGET: budget,
                config.COL_WISH_DAYS: float(rng.choice(DAY_CHOICES[tour_type])),
                config.COL_WISH_TYPE: tour_type,
                config.COL_WISH_COMPANION: companion,
                config.COL_TRAVELERS: int(rng.choice(TRAVELERS[companion])),
                config.COL_SPLIT: split,
            })
    return wishes


def main() -> None:
    tours = load_tours()
    rows = []
    for n, w in enumerate(generate(np.random.default_rng(SEED)), start=1):
        expected, kind, motivation = explain_rubric(tours, w[config.COL_BUDGET], w[config.COL_WISH_DAYS],
                                                    w[config.COL_WISH_TYPE], w[config.COL_WISH_COMPANION])
        rows.append({config.COL_WISH_ID: f"W{n:02d}", **{k: w[k] for k in (
            config.COL_BUDGET, config.COL_WISH_DAYS, config.COL_WISH_TYPE, config.COL_WISH_COMPANION, config.COL_TRAVELERS)},
            config.COL_WISH_KIND: kind, config.COL_EXPECTED: expected, config.COL_MOTIVATION: motivation,
            config.COL_SPLIT: w[config.COL_SPLIT]})
    df = pd.DataFrame(rows, columns=config.WISH_COLUMNS)
    df.to_csv(config.TEST_WISHES_CSV, index=False)
    print(f"{len(df)} wensen -> {config.TEST_WISHES_CSV}")
    print(pd.crosstab(df[config.COL_WISH_KIND], df[config.COL_SPLIT], margins=True))


if __name__ == "__main__":
    main()
