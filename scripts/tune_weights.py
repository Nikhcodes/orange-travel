"""Tune the feature weights on the development wishes, then measure once on the test wishes.

Run:  uv run python -m scripts.tune_weights
Copy the chosen weights into config.FINAL_WEIGHTS if they differ.
"""

from src import config
from src.data_loader import load_test_wishes, load_tours
from src.experiments import best_weights, score, split, tune_weights


def main() -> None:
    tours = load_tours()
    wishes = load_test_wishes(tours=tours)
    dev, test = split(wishes, config.SPLIT_DEV), split(wishes, config.SPLIT_TEST)
    table = tune_weights(tours, dev)
    print("Top 10 op de ONTWIKKEL-set:")
    print(table.head(10).to_string(index=False))
    weights = best_weights(table)
    print(f"\nGekozen gewichten:      {weights}")
    print(f"In config.FINAL_WEIGHTS: {config.FINAL_WEIGHTS}")
    for name, data in (("ontwikkel", dev), ("test", test)):
        for label, w in (("neutraal (alle 1)", {}), ("getuned", weights)):
            r = score(tours, data, w)
            print(f"{name:9} | {label:17} | top-1 {r['top1']}/{r['n']} | top-3 {r['top3']}/{r['n']} | "
                  f"soort klopt {r['type_match']:.0%} | budget {r['budget']:.0%}")


if __name__ == "__main__":
    main()
