"""Tune the feature weights on the development wishes, then measure once on the test wishes.

Run from the project root:
    uv run python -m scripts.tune_weights
"""

from src import config
from src.data_loader import load_destinations, load_test_customers
from src.experiments import best_weights, score, split, tune_weights


def main() -> None:
    destinations = load_destinations()
    scenarios = load_test_customers(destinations=destinations)
    dev, test = split(scenarios, config.SPLIT_DEV), split(scenarios, config.SPLIT_TEST)

    table = tune_weights(destinations, dev)
    print("Top 10 gewichten op de ONTWIKKEL-set:")
    print(table.head(10).to_string(index=False))

    weights = best_weights(table)
    print(f"\nGekozen gewichten: {weights}")
    print(f"In config.FINAL_WEIGHTS staat: {config.FINAL_WEIGHTS}")

    for name, data in (("ontwikkel", dev), ("test", test)):
        for label, w in (("neutraal (alle 1)", {}), ("getuned", weights)):
            r = score(destinations, data, w)
            print(f"{name:9} | {label:17} | top-1 {r['top1']}/{r['n']} | top-3 {r['top3']}/{r['n']}")


if __name__ == "__main__":
    main()
