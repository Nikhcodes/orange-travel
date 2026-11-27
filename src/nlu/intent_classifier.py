"""Intent classifier: what does the customer want with this message?

Supervised machine learning: TF-IDF features (words + character n-grams, robust to
typos) and a logistic regression, trained on the labelled sentences in data/intents.csv.

- `train_and_evaluate()` does a stratified train/test split (75/25) and reports the
  confusion matrix, precision, recall and F1 on the held-out test part.
- `IntentClassifier.load()` trains on ALL sentences for use in the chatbot.
Below CONFIDENCE_THRESHOLD the bot says it did not understand (FR-15).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from src import config

CONFIDENCE_THRESHOLD = 0.30
RANDOM_STATE = 42


def load_intents(path=config.INTENTS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8").dropna()
    df["tekst"] = df["tekst"].astype(str).str.strip()
    return df[df["tekst"] != ""].reset_index(drop=True)


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True, sublinear_tf=True)),
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), lowercase=True, sublinear_tf=True)),
    ])
    classifier = LogisticRegression(C=10, max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)
    return Pipeline([("features", features), ("classifier", classifier)])


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    understood: bool


class IntentClassifier:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.labels = list(pipeline.classes_)

    @classmethod
    def load(cls) -> "IntentClassifier":
        data = load_intents()
        pipeline = build_pipeline().fit(data["tekst"], data["intent"])
        return cls(pipeline)

    def knows_any_word(self, text: str) -> bool:
        """True if at least one word of the text occurs in the training vocabulary."""
        words = self.pipeline.named_steps["features"].transformer_list[0][1]
        analyzer = words.build_analyzer()
        return any(token in words.vocabulary_ for token in analyzer(text))

    def predict(self, text: str) -> IntentPrediction:
        probabilities = self.pipeline.predict_proba([text])[0]
        best = int(np.argmax(probabilities))
        confidence = float(probabilities[best])
        return IntentPrediction(self.labels[best], confidence, confidence >= CONFIDENCE_THRESHOLD)


@dataclass
class IntentEvaluation:
    labels: list[str]
    matrix: pd.DataFrame
    report: pd.DataFrame
    accuracy: float
    macro_f1: float
    n_train: int
    n_test: int
    errors: pd.DataFrame


def train_and_evaluate(test_size: float = 0.25) -> IntentEvaluation:
    data = load_intents()
    x_train, x_test, y_train, y_test = train_test_split(
        data["tekst"], data["intent"], test_size=test_size, stratify=data["intent"], random_state=RANDOM_STATE)
    pipeline = build_pipeline().fit(x_train, y_train)
    predicted = pipeline.predict(x_test)
    labels = sorted(data["intent"].unique())
    matrix = pd.DataFrame(confusion_matrix(y_test, predicted, labels=labels), index=labels, columns=labels)
    report = pd.DataFrame(classification_report(y_test, predicted, labels=labels, output_dict=True,
                                                zero_division=0)).T
    errors = pd.DataFrame({"tekst": x_test, "verwacht": y_test, "voorspeld": predicted})
    errors = errors[errors["verwacht"] != errors["voorspeld"]].reset_index(drop=True)
    return IntentEvaluation(labels, matrix, report.round(3), float(report.loc["accuracy", "precision"]),
                            float(report.loc["macro avg", "f1-score"]), len(x_train), len(x_test), errors)
