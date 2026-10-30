from __future__ import annotations

import json

import numpy as np
import pytest

from apps.ml.training.dataset import DatasetBundle, DatasetLabel, DatasetSchemaError, TrainingExample, normalize_splits
from apps.ml.training.model import UnfairToSClassifier, _test_metrics, train_baseline


def test_normalize_splits_uses_source_label_order_and_audits_duplicates() -> None:
    labels = ["Choice of law", "Limitation of liability"]
    raw = {
        "train": [
            {"text": "  Example   Clause A ", "labels": [1]},
            {"text": "example clause a", "labels": [0]},
        ],
        "validation": [{"text": "Example clause B", "labels": [0]}],
        "test": [{"text": "Example clause C", "labels": []}],
    }

    splits, duplicate_audit = normalize_splits(raw, labels)

    assert splits["train"][0].labels == ("limitation_of_liability",)
    assert splits["train"][1].labels == ("choice_of_law",)
    assert duplicate_audit["within_split_duplicate_rows"]["train"] == 1
    assert duplicate_audit["cross_split_shared_unique_texts"]["train_validation"] == 0
    assert duplicate_audit["source_document_identifier_available"] is False


def test_normalize_splits_rejects_unknown_metadata_labels() -> None:
    raw = {
        "train": [{"text": "Clause", "labels": [4]}],
        "validation": [{"text": "Clause 2", "labels": []}],
        "test": [{"text": "Clause 3", "labels": []}],
    }
    with pytest.raises(DatasetSchemaError, match="Unknown label"):
        normalize_splits(raw, ["Only label"])


def _toy_bundle() -> DatasetBundle:
    labels = (
        DatasetLabel(0, "Limitation of liability", "limitation_of_liability"),
        DatasetLabel(1, "Arbitration", "arbitration"),
    )
    train = []
    for index in range(12):
        train.append(TrainingExample(f"train:{index}", f"liability limit clause number {index}", (labels[0].slug,)))
        train.append(TrainingExample(f"train:{index + 12}", f"private arbitration forum number {index}", (labels[1].slug,)))
        train.append(TrainingExample(f"train:{index + 24}", f"ordinary service description number {index}", ()))
    validation = (
        TrainingExample("validation:0", "liability cap and limits", (labels[0].slug,)),
        TrainingExample("validation:1", "arbitration forum", (labels[1].slug,)),
        TrainingExample("validation:2", "general service information", ()),
    )
    test = (
        TrainingExample("test:0", "liability cap clause", (labels[0].slug,)),
        TrainingExample("test:1", "arbitration forum clause", (labels[1].slug,)),
        TrainingExample("test:2", "general account information", ()),
    )
    manifest = {"dataset": {"repository": "synthetic-test-fixture", "license": ["synthetic"]}, "split_counts": {}}
    return DatasetBundle(tuple(train), validation, test, labels, manifest)


def test_model_artifact_loads_and_returns_shared_contract(tmp_path) -> None:
    result = train_baseline(_toy_bundle(), tmp_path / "classifier", random_seed=17)
    artifact_dir = tmp_path / "classifier"
    loaded = UnfairToSClassifier.load(artifact_dir)
    prediction = loaded.predict("liability cap clause")
    metadata = json.loads((artifact_dir / "classifier_metadata.json").read_text(encoding="utf-8"))

    assert prediction.classifier_version == metadata["classifier_version"]
    assert {item.label for item in prediction.predictions} == {"limitation_of_liability", "arbitration"}
    assert all(0 <= item.score <= 1 and 0 <= item.threshold <= 1 for item in prediction.predictions)
    assert result["metrics"]["held_out_test"]["evaluation_count"] == 1
    assert (artifact_dir / "dataset_manifest.json").is_file()
    assert (artifact_dir / "metrics.json").is_file()


def test_model_loader_rejects_changed_artifact(tmp_path) -> None:
    artifact_dir = tmp_path / "classifier"
    train_baseline(_toy_bundle(), artifact_dir)
    classifier_path = artifact_dir / "one_vs_rest_logistic_regression.joblib"
    classifier_path.write_bytes(classifier_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="integrity check failed"):
        UnfairToSClassifier.load(artifact_dir)


def test_false_negative_summary_separates_records_assignments_and_sentences() -> None:
    labels = (
        DatasetLabel(0, "Topic A", "topic_a"),
        DatasetLabel(1, "Topic B", "topic_b"),
    )
    test = (
        TrainingExample("test:0", "shared miss", ("topic_a", "topic_b")),
        TrainingExample("test:1", "second miss", ("topic_a",)),
        TrainingExample("test:2", "detected topic b", ("topic_b",)),
        TrainingExample("test:3", "negative", ()),
    )
    bundle = DatasetBundle((), (), test, labels, {"duplicate_audit": {}})
    y_true = np.array([[1, 1], [1, 0], [0, 1], [0, 0]], dtype="int8")
    scores = np.array(
        [[0.1, 0.1], [0.1, 0.2], [0.2, 0.9], [0.9, 0.1]], dtype=float
    )

    metrics = _test_metrics(bundle, y_true, scores, {"topic_a": 0.5, "topic_b": 0.5})

    assert metrics["false_negative_summary"] == {
        "saved_example_records": 3,
        "saved_unique_example_ids": 2,
        "missed_label_assignments": 3,
        "unique_affected_sentences": 2,
        "saved_examples_per_label_cap": 3,
        "note": "The example list is capped at three records per label; aggregate counts use the full held-out prediction matrix from this single evaluation.",
    }
