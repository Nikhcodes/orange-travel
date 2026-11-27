"""Check all data files and the rubric labels.

Run:  uv run python -m scripts.validate_data
"""

import sys

import pandas as pd

from src import config
from src.data_loader import DatasetError, load_test_wishes, load_tours
from src.nlu.intent_classifier import load_intents
from src.rubric import rubric_best


def main() -> int:
    try:
        tours = load_tours()
        wishes = load_test_wishes(tours=tours)
        intents = load_intents()
        kb = pd.read_csv(config.KNOWLEDGE_CSV)
    except DatasetError as exc:
        print(f"FOUT: {exc}")
        return 1
    print(f"OK  tours.csv          {len(tours)} tours")
    print(pd.crosstab(tours[config.COL_TYPE], tours[config.COL_INTENSITY], margins=True).to_string(), "\n")
    print(f"OK  test_wishes.csv    {len(wishes)} wensen "
          f"({(wishes[config.COL_SPLIT] == config.SPLIT_DEV).sum()} ontwikkel / {(wishes[config.COL_SPLIT] == config.SPLIT_TEST).sum()} test)")
    print(f"OK  intents.csv        {len(intents)} zinnen, {intents['intent'].nunique()} intenties")
    bad_links = kb[~kb["bron"].str.startswith("https://www.orangesuriname.com/")]
    if not bad_links.empty:
        print(f"FOUT: knowledge_base.csv heeft bronnen buiten orangesuriname.com: {bad_links['onderwerp'].tolist()}")
        return 1
    print(f"OK  knowledge_base.csv {len(kb)} onderwerpen, alle bronnen op orangesuriname.com")
    wrong = [r[config.COL_WISH_ID] for _, r in wishes.iterrows() if rubric_best(
        tours, r[config.COL_BUDGET], r[config.COL_WISH_DAYS], r[config.COL_WISH_TYPE], r[config.COL_WISH_COMPANION]) != r[config.COL_EXPECTED]]
    if wrong:
        print(f"FOUT: labels volgen de rubriek niet meer: {wrong}")
        return 1
    print("OK  alle verwachte uitkomsten volgen de rubriek (FR-07)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
