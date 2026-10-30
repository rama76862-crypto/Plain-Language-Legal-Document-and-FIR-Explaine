"""Word/character TF-IDF one-vs-rest baseline and checked local artifact adapter."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn import __version__ as sklearn_version
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression

from apps.ml.service.contracts import ClassifierPrediction, ClassifierResult

from .dataset import DatasetBundle, DatasetLabel, TrainingExample
from .progress import PhaseProgress

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_FORMAT_VERSION = 1
CLASSIFIER_VERSION_PREFIX = "lexglue-unfair-tos-word-char-ovr-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _label_matrix(examples: tuple[TrainingExample, ...], labels: tuple[DatasetLabel, ...]) -> np.ndarray:
    label_index = {label.slug: label.index for label in labels}
    matrix = np.zeros((len(examples), len(labels)), dtype=np.int8)
    for row_index, example in enumerate(examples):
        for slug in example.labels:
            if slug not in label_index:
                raise ValueError(f"Unknown normalized label in example {example.example_id}")
            matrix[row_index, label_index[slug]] = 1
    return matrix


def _new_feature_union() -> FeatureUnion:
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=200_000,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=250_000,
                    sublinear_tf=True,
                ),
            ),
        ],
        n_jobs=1,
    )


def _score_matrix(estimator: OneVsRestClassifier, features: Any, label_count: int) -> np.ndarray:
    scores = np.asarray(estimator.predict_proba(features), dtype=np.float64)
    if scores.ndim == 1:
        scores = scores.reshape(-1, 1)
    if scores.shape[1] != label_count:
        raise RuntimeError(f"Classifier returned {scores.shape[1]} labels; expected {label_count}")
    return np.clip(scores, 0.0, 1.0)


def _tune_thresholds(y_true: np.ndarray, scores: np.ndarray, labels: tuple[DatasetLabel, ...]) -> tuple[dict[str, float], dict[str, Any]]:
    thresholds: dict[str, float] = {}
    details: dict[str, Any] = {}
    for label in labels:
        column = label.index
        positives = int(y_true[:, column].sum())
        if positives == 0:
            thresholds[label.slug] = 0.5
            details[label.slug] = {
                "threshold": 0.5,
                "validation_support": 0,
                "selection": "default_0.5_no_positive_validation_examples",
            }
            continue

        candidates = np.unique(np.concatenate(([0.0, 1.0], scores[:, column])))
        best_f1 = -1.0
        best_precision = -1.0
        best_threshold = 0.5
        for candidate in candidates:
            predicted = scores[:, column] >= candidate
            true = y_true[:, column].astype(bool)
            tp = int(np.logical_and(predicted, true).sum())
            fp = int(np.logical_and(predicted, ~true).sum())
            fn = int(np.logical_and(~predicted, true).sum())
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
            if (f1, precision, float(candidate)) > (best_f1, best_precision, best_threshold):
                best_f1 = f1
                best_precision = precision
                best_threshold = float(candidate)
        thresholds[label.slug] = best_threshold
        details[label.slug] = {
            "threshold": best_threshold,
            "validation_support": positives,
            "validation_f1_at_threshold": best_f1,
            "selection": "maximum_validation_f1_then_precision_then_higher_threshold",
        }
    return thresholds, details


def _threshold_predictions(scores: np.ndarray, labels: tuple[DatasetLabel, ...], thresholds: dict[str, float]) -> np.ndarray:
    return np.column_stack([scores[:, label.index] >= thresholds[label.slug] for label in labels]).astype(np.int8)


def _test_metrics(
    bundle: DatasetBundle,
    y_true: np.ndarray,
    scores: np.ndarray,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Compute held-out metrics once, using thresholds already fixed from validation."""
    y_pred = _threshold_predictions(scores, bundle.labels, thresholds)
    precisions, recalls, f1s, supports = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=None,
        zero_division=0,
    )
    per_label = {}
    for label in bundle.labels:
        idx = label.index
        per_label[label.slug] = {
            "source_name": label.source_name,
            "precision": float(precisions[idx]),
            "recall": float(recalls[idx]),
            "f1": float(f1s[idx]),
            "support": int(supports[idx]),
            "threshold": thresholds[label.slug],
        }

    false_negatives: list[dict[str, Any]] = []
    missed_label_assignments = 0
    affected_test_rows: set[int] = set()
    for label in bundle.labels:
        idx = label.index
        missed = np.flatnonzero((y_true[:, idx] == 1) & (y_pred[:, idx] == 0))
        missed_label_assignments += int(len(missed))
        affected_test_rows.update(int(row) for row in missed)
        ranked = sorted(missed.tolist(), key=lambda row: scores[row, idx], reverse=True)[:3]
        for row in ranked:
            example = bundle.test[row]
            false_negatives.append(
                {
                    "example_id": example.example_id,
                    "missed_label": label.slug,
                    "score": float(scores[row, idx]),
                    "threshold": thresholds[label.slug],
                    "true_labels": list(example.labels),
                    "predicted_labels": [
                        candidate.slug
                        for candidate in bundle.labels
                        if y_pred[row, candidate.index] == 1
                    ],
                    "text_excerpt": example.text[:320],
                }
            )

    duplicate_audit = bundle.manifest.get("duplicate_audit", {})
    shared_texts = duplicate_audit.get("cross_split_shared_unique_texts", {})
    overlap_summary = ", ".join(
        f"{split}={count}"
        for split, count in shared_texts.items()
        if int(count) > 0
    )
    caveats = []
    if overlap_summary:
        caveats.append(
            "Normalized exact-text overlaps across the preserved official splits: "
            + overlap_summary
            + ". The source has no document identifier for a document-level split; these overlaps may make held-out metrics optimistic."
        )

    return {
        "split": "test",
        "evaluation_count": 1,
        "examples": len(bundle.test),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "micro_f1": float(f1_score(y_true, y_pred, average="micro", zero_division=0)),
        "per_label": per_label,
        "false_negative_examples": false_negatives,
        "false_negative_summary": {
            "saved_example_records": len(false_negatives),
            "saved_unique_example_ids": len({entry["example_id"] for entry in false_negatives}),
            "missed_label_assignments": missed_label_assignments,
            "unique_affected_sentences": len(affected_test_rows),
            "saved_examples_per_label_cap": 3,
            "note": "The example list is capped at three records per label; aggregate counts use the full held-out prediction matrix from this single evaluation.",
        },
        "caveats": caveats,
        "note": "UNFAIR-ToS labels are European terms-of-service concern cues, not Indian enforceability findings. An empty prediction means no configured cue was detected, not that the clause is safe.",
    }


def train_baseline(
    bundle: DatasetBundle,
    output_dir: Path | str = DEFAULT_ARTIFACT_DIR,
    *,
    random_seed: int = 17,
) -> dict[str, Any]:
    """Fit train-only TF-IDF + one-vs-rest logistic regression and evaluate test once."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not bundle.train or not bundle.validation or not bundle.test:
        raise ValueError("Train, validation, and test splits must all contain examples")
    if not bundle.labels:
        raise ValueError("Dataset metadata must define at least one label")

    train_texts = [example.text for example in bundle.train]
    validation_texts = [example.text for example in bundle.validation]
    test_texts = [example.text for example in bundle.test]
    y_train = _label_matrix(bundle.train, bundle.labels)
    y_validation = _label_matrix(bundle.validation, bundle.labels)
    y_test = _label_matrix(bundle.test, bundle.labels)
    feature_union = _new_feature_union()
    estimator = OneVsRestClassifier(
        LogisticRegression(
            solver="liblinear",
            class_weight="balanced",
            max_iter=1000,
            random_state=random_seed,
        ),
        n_jobs=1,
    )
    timings: dict[str, float] = {}

    with PhaseProgress("Classifier phases", total=5) as progress:
        started = time.perf_counter()
        train_features = feature_union.fit_transform(train_texts)
        timings["fit_word_and_character_tfidf_seconds"] = time.perf_counter() - started
        progress.advance("word and character TF-IDF fitted on train only")

        started = time.perf_counter()
        estimator.fit(train_features, y_train)
        timings["fit_one_vs_rest_logistic_regression_seconds"] = time.perf_counter() - started
        progress.advance(f"{len(estimator.estimators_)} binary logistic estimators fitted")

        started = time.perf_counter()
        validation_features = feature_union.transform(validation_texts)
        validation_scores = _score_matrix(estimator, validation_features, len(bundle.labels))
        thresholds, threshold_details = _tune_thresholds(y_validation, validation_scores, bundle.labels)
        timings["validation_threshold_tuning_seconds"] = time.perf_counter() - started
        progress.advance("per-label thresholds selected from validation")

        started = time.perf_counter()
        test_features = feature_union.transform(test_texts)
        test_scores = _score_matrix(estimator, test_features, len(bundle.labels))
        test_metrics = _test_metrics(bundle, y_test, test_scores, thresholds)
        timings["held_out_test_evaluation_seconds"] = time.perf_counter() - started
        progress.advance("held-out test evaluated once")

        started = time.perf_counter()
        vectorizer_path = output_path / "tfidf_features.joblib"
        classifier_path = output_path / "one_vs_rest_logistic_regression.joblib"
        joblib.dump(feature_union, vectorizer_path, compress=3)
        joblib.dump(estimator, classifier_path, compress=3)
        artifacts = {
            "features": {"file": vectorizer_path.name, "sha256": _sha256(vectorizer_path)},
            "classifier": {"file": classifier_path.name, "sha256": _sha256(classifier_path)},
        }
        classifier_version = f"{CLASSIFIER_VERSION_PREFIX}-{artifacts['classifier']['sha256'][:12]}"
        metadata = {
            "artifact_format_version": ARTIFACT_FORMAT_VERSION,
            "classifier_version": classifier_version,
            "trust_policy": "locally trained artifact only; verify hashes and never load model files from an untrusted source",
            "dataset": bundle.manifest.get("dataset", {}),
            "label_mapping": [
                {"index": label.index, "source_name": label.source_name, "slug": label.slug}
                for label in bundle.labels
            ],
            "thresholds": thresholds,
            "training_config": {
                "feature_union": {
                    "word": {"analyzer": "word", "ngram_range": [1, 2], "min_df": 2, "max_features": 200000, "sublinear_tf": True, "strip_accents": "unicode"},
                    "character": {"analyzer": "char_wb", "ngram_range": [3, 5], "min_df": 2, "max_features": 250000, "sublinear_tf": True},
                },
                "estimator": "OneVsRestClassifier(LogisticRegression)",
                "solver": "liblinear",
                "class_weight": "balanced",
                "max_iter": 1000,
                "random_seed": random_seed,
                "text_preprocessing_fit_split": "train only",
                "threshold_tuning_split": "validation",
                "test_evaluations": 1,
            },
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scikit_learn": sklearn_version,
                "scipy": _package_version("scipy"),
                "joblib": _package_version("joblib"),
            },
            "artifacts": artifacts,
        }
        metrics = {
            "validation_thresholds": threshold_details,
            "held_out_test": test_metrics,
            "timings_seconds": timings,
            "split_counts": {
                "train": len(bundle.train),
                "validation": len(bundle.validation),
                "test": len(bundle.test),
            },
        }
        _write_json(output_path / "dataset_manifest.json", bundle.manifest)
        _write_json(output_path / "classifier_metadata.json", metadata)
        _write_json(output_path / "metrics.json", metrics)
        timings["artifact_write_seconds"] = time.perf_counter() - started
        _write_json(output_path / "metrics.json", metrics)
        progress.advance("model, metadata, manifest, and evaluation artifacts saved")

    return {"metadata": metadata, "metrics": metrics, "artifact_dir": str(output_path.resolve())}


class UnfairToSClassifier:
    """Adapter used by the private service; it returns all labels and real thresholds."""

    def __init__(self, feature_union: FeatureUnion, estimator: OneVsRestClassifier, metadata: dict[str, Any]) -> None:
        self._feature_union = feature_union
        self._estimator = estimator
        self._metadata = metadata
        self._labels = metadata["label_mapping"]
        self._thresholds = metadata["thresholds"]
        self.classifier_version = metadata["classifier_version"]

    @classmethod
    def load(cls, artifact_dir: Path | str = DEFAULT_ARTIFACT_DIR) -> "UnfairToSClassifier":
        """Load a local training artifact after checking its generated metadata and file hashes."""
        root = Path(artifact_dir)
        metadata_path = root / "classifier_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("artifact_format_version") != ARTIFACT_FORMAT_VERSION:
            raise ValueError("Unsupported classifier artifact format")
        if not str(metadata.get("classifier_version", "")).startswith(CLASSIFIER_VERSION_PREFIX):
            raise ValueError("Artifact does not identify the expected local UNFAIR-ToS baseline")
        artifacts = metadata.get("artifacts", {})
        expected = {}
        for key in ("features", "classifier"):
            entry = artifacts.get(key, {})
            name = entry.get("file")
            digest = entry.get("sha256")
            if not name or not digest:
                raise ValueError(f"Missing trusted artifact metadata for {key}")
            path = root / name
            if not path.is_file() or _sha256(path) != digest:
                raise ValueError(f"Artifact integrity check failed for {name}")
            expected[key] = path
        # joblib uses pickle internally: caller must point only at this locally produced,
        # hash-verified artifact directory, never a downloaded or user-supplied file.
        feature_union = joblib.load(expected["features"])
        estimator = joblib.load(expected["classifier"])
        if len(metadata.get("label_mapping", [])) != len(metadata.get("thresholds", {})):
            raise ValueError("Classifier label and threshold mappings do not match")
        return cls(feature_union, estimator, metadata)

    def predict(self, text: str) -> ClassifierResult:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Classifier input text must be non-empty")
        features = self._feature_union.transform([text])
        scores = _score_matrix(self._estimator, features, len(self._labels))[0]
        predictions = []
        for label in self._labels:
            slug = label["slug"]
            threshold = float(self._thresholds[slug])
            score = float(scores[int(label["index"])])
            predictions.append(
                ClassifierPrediction(
                    label=slug,
                    score=score,
                    threshold=threshold,
                    detected=score >= threshold,
                )
            )
        return ClassifierResult(predictions=predictions, classifier_version=self.classifier_version)
