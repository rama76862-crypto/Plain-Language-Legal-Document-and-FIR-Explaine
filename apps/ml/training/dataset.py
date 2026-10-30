"""Pinned LexGLUE UNFAIR-ToS data loading and source manifest creation."""

from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from typing import Any, Mapping

from .progress import status, tracked

DATASET_REPO = "coastalcph/lex_glue"
DATASET_CONFIG = "unfair_tos"
DATASET_REVISION = "c23fdff1a6bf74e0e1a71cb86f1e781d37da888c"
DATASET_CARD_URL = f"https://huggingface.co/datasets/{DATASET_REPO}/tree/{DATASET_REVISION}/{DATASET_CONFIG}"
DATASET_FILE_PATHS = {
    "train": f"{DATASET_CONFIG}/train-00000-of-00001.parquet",
    "validation": f"{DATASET_CONFIG}/validation-00000-of-00001.parquet",
    "test": f"{DATASET_CONFIG}/test-00000-of-00001.parquet",
}
OFFICIAL_SPLITS = ("train", "validation", "test")
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


class DatasetSchemaError(ValueError):
    """Raised when the pinned public source no longer matches its declared schema."""


@dataclass(frozen=True)
class DatasetLabel:
    index: int
    source_name: str
    slug: str


@dataclass(frozen=True)
class TrainingExample:
    example_id: str
    text: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class DatasetBundle:
    train: tuple[TrainingExample, ...]
    validation: tuple[TrainingExample, ...]
    test: tuple[TrainingExample, ...]
    labels: tuple[DatasetLabel, ...]
    manifest: dict[str, Any]

    @property
    def label_slugs(self) -> tuple[str, ...]:
        return tuple(label.slug for label in self.labels)


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    if not slug:
        raise DatasetSchemaError(f"Cannot create a stable label slug from {label!r}")
    return slug


def _label_definitions(source_names: list[str]) -> tuple[DatasetLabel, ...]:
    labels = tuple(DatasetLabel(index=i, source_name=name, slug=_slugify(name)) for i, name in enumerate(source_names))
    slugs = [label.slug for label in labels]
    if len(slugs) != len(set(slugs)):
        raise DatasetSchemaError("Dataset metadata produced duplicate normalized label slugs")
    if not labels:
        raise DatasetSchemaError("Dataset metadata contains no class labels")
    return labels


def _get_field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _license_values(card_data: Any) -> list[str]:
    value = _get_field(card_data, "license")
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item]
    return [str(value)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_sha_from_metadata(file_info: Any) -> str | None:
    lfs = _get_field(file_info, "lfs")
    return _get_field(lfs, "sha256") if lfs is not None else None


def _expected_counts_from_card(card_data: Any) -> dict[str, int]:
    dataset_infos = _get_field(card_data, "dataset_info", []) or []
    for config in dataset_infos:
        if _get_field(config, "config_name") != DATASET_CONFIG:
            continue
        splits = _get_field(config, "splits", []) or []
        return {
            str(_get_field(split, "name")): int(_get_field(split, "num_examples"))
            for split in splits
            if _get_field(split, "name") and _get_field(split, "num_examples") is not None
        }
    return {}


def _class_label_names(dataset_dict: Any) -> list[str]:
    first_split = dataset_dict[OFFICIAL_SPLITS[0]]
    features = first_split.features
    if "text" not in features or "labels" not in features:
        raise DatasetSchemaError(f"Expected text and labels columns, received {list(features)}")
    label_feature = getattr(features["labels"], "feature", None)
    names = getattr(label_feature, "names", None)
    if not names:
        raise DatasetSchemaError("The labels feature has no ClassLabel names in source metadata")
    source_names = [str(name) for name in names]
    for split_name in OFFICIAL_SPLITS[1:]:
        other = dataset_dict[split_name].features
        other_feature = getattr(other.get("labels"), "feature", None)
        if list(getattr(other_feature, "names", []) or []) != list(names):
            raise DatasetSchemaError(f"The {split_name} label mapping differs from the train metadata")
    return source_names


def _normalize_label_values(values: Any, labels: tuple[DatasetLabel, ...], split: str, row_index: int) -> tuple[str, ...]:
    by_index = {label.index: label for label in labels}
    by_name = {label.source_name: label for label in labels}
    normalized: list[str] = []
    for value in values:
        if isinstance(value, Integral):
            label = by_index.get(int(value))
        else:
            label = by_name.get(str(value))
        if label is None:
            raise DatasetSchemaError(f"Unknown label value in {split} row {row_index}")
        if label.slug not in normalized:
            normalized.append(label.slug)
    return tuple(normalized)


def normalize_splits(
    raw_splits: Mapping[str, Any],
    source_label_names: list[str],
) -> tuple[dict[str, tuple[TrainingExample, ...]], dict[str, Any]]:
    """Normalize rows after the source feature metadata has supplied label order."""
    missing = [split for split in OFFICIAL_SPLITS if split not in raw_splits]
    if missing:
        raise DatasetSchemaError(f"Missing official dataset splits: {', '.join(missing)}")
    labels = _label_definitions(source_label_names)
    normalized: dict[str, tuple[TrainingExample, ...]] = {}

    for split_name in OFFICIAL_SPLITS:
        raw_split = raw_splits[split_name]
        total = len(raw_split)
        examples: list[TrainingExample] = []
        for row_index, row in enumerate(tracked(raw_split, total=total, description=f"Preparing {split_name}")):
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                raise DatasetSchemaError(f"Empty or non-text content in {split_name} row {row_index}")
            label_values = row.get("labels")
            if label_values is None:
                raise DatasetSchemaError(f"Missing labels in {split_name} row {row_index}")
            examples.append(
                TrainingExample(
                    example_id=f"{split_name}:{row_index}",
                    text=text,
                    labels=_normalize_label_values(label_values, labels, split_name, row_index),
                )
            )
        normalized[split_name] = tuple(examples)

    canonical = {
        split: [re.sub(r"\s+", " ", example.text.casefold()).strip() for example in examples]
        for split, examples in normalized.items()
    }
    duplicate_rows = {
        split: sum(count - 1 for count in Counter(texts).values() if count > 1)
        for split, texts in canonical.items()
    }
    unique_texts = {split: set(texts) for split, texts in canonical.items()}
    cross_split = {
        "train_validation": len(unique_texts["train"] & unique_texts["validation"]),
        "train_test": len(unique_texts["train"] & unique_texts["test"]),
        "validation_test": len(unique_texts["validation"] & unique_texts["test"]),
    }
    duplicate_audit = {
        "within_split_duplicate_rows": duplicate_rows,
        "cross_split_shared_unique_texts": cross_split,
        "normalization": "casefold and collapse whitespace",
        "source_document_identifier_available": False,
        "split_policy": "official train/validation/test splits retained unchanged; no new split created",
    }
    return normalized, duplicate_audit


def _source_metadata(cache_root: Path) -> tuple[Any, dict[str, Any]]:
    # Keep both Hub downloads and Arrow caches inside the ignored project cache rather
    # than the user's global Hugging Face cache.
    huggingface_cache = cache_root / "huggingface"
    datasets_cache = cache_root / "datasets"
    os.environ["HF_HOME"] = str(cache_root / "hf_home")
    os.environ["HF_HUB_CACHE"] = str(huggingface_cache)
    os.environ["HF_DATASETS_CACHE"] = str(datasets_cache)
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise RuntimeError("huggingface-hub is required to inspect and download LexGLUE metadata") from exc

    cache_root.mkdir(parents=True, exist_ok=True)
    with status("Inspecting the pinned LexGLUE dataset metadata"):
        info = HfApi().dataset_info(
            DATASET_REPO,
            revision=DATASET_REVISION,
            files_metadata=True,
        )
    if getattr(info, "sha", None) != DATASET_REVISION:
        raise DatasetSchemaError("Hugging Face returned a different revision than the pinned dataset commit")

    card_data = getattr(info, "card_data", None)
    licenses = _license_values(card_data)
    if not licenses:
        raise DatasetSchemaError("The pinned dataset card has no declared license; refusing to download it")

    siblings = {getattr(entry, "rfilename", ""): entry for entry in getattr(info, "siblings", [])}
    file_manifest: dict[str, Any] = {}
    for split_name, repo_path in DATASET_FILE_PATHS.items():
        file_info = siblings.get(repo_path)
        if file_info is None:
            raise DatasetSchemaError(f"Pinned source is missing expected split file {repo_path}")
        with status(f"Downloading LexGLUE UNFAIR-ToS {split_name} parquet"):
            downloaded = Path(
                hf_hub_download(
                    repo_id=DATASET_REPO,
                    filename=repo_path,
                    repo_type="dataset",
                    revision=DATASET_REVISION,
                    cache_dir=str(huggingface_cache),
                )
            )
        actual_sha = _sha256(downloaded)
        expected_sha = _file_sha_from_metadata(file_info)
        if expected_sha and actual_sha.casefold() != str(expected_sha).casefold():
            raise DatasetSchemaError(f"Downloaded content hash does not match Hub metadata for {repo_path}")
        try:
            relative_path = str(downloaded.resolve().relative_to(cache_root.resolve()))
        except ValueError:
            relative_path = downloaded.name
        file_manifest[split_name] = {
            "repo_path": repo_path,
            "cache_path": relative_path,
            "size_bytes": downloaded.stat().st_size,
            "sha256": actual_sha,
            "hub_sha256": expected_sha,
            "hub_blob_id": getattr(file_info, "blob_id", None),
        }
    metadata = {
        "repository": DATASET_REPO,
        "config": DATASET_CONFIG,
        "revision": info.sha,
        "license": licenses,
        "source_url": DATASET_CARD_URL,
        "source_files": file_manifest,
        "expected_split_counts_from_card": _expected_counts_from_card(card_data),
    }
    return info, metadata


def load_lexglue_unfair_tos(cache_dir: Path | str | None = None) -> DatasetBundle:
    """Download and parse only the pinned UNFAIR-ToS configuration and its official splits."""
    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root = cache_root.resolve()
    _, source = _source_metadata(cache_root)
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("datasets is required to parse the pinned LexGLUE parquet files") from exc

    with status("Parsing only the pinned LexGLUE UNFAIR-ToS configuration"):
        dataset_dict = load_dataset(
            DATASET_REPO,
            name=DATASET_CONFIG,
            revision=DATASET_REVISION,
            cache_dir=str(cache_root / "datasets"),
        )
    available_splits = set(dataset_dict.keys())
    if available_splits != set(OFFICIAL_SPLITS):
        raise DatasetSchemaError(f"Unexpected source splits: {sorted(available_splits)}")

    source_label_names = _class_label_names(dataset_dict)
    normalized, duplicate_audit = normalize_splits(dataset_dict, source_label_names)
    split_counts = {split: len(normalized[split]) for split in OFFICIAL_SPLITS}
    expected_counts = source.get("expected_split_counts_from_card", {})
    if expected_counts and any(split_counts.get(split) != count for split, count in expected_counts.items()):
        raise DatasetSchemaError(
            f"Loaded split counts {split_counts} do not match the pinned card metadata {expected_counts}"
        )

    labels = _label_definitions(source_label_names)
    manifest = {
        "dataset": source,
        "feature_schema": {
            "columns": ["text", "labels"],
            "text": "string",
            "labels": "sequence of ClassLabel IDs decoded using source metadata order",
            "source_label_names": source_label_names,
        },
        "label_mapping": [
            {"index": label.index, "source_name": label.source_name, "internal_slug": label.slug}
            for label in labels
        ],
        "split_counts": split_counts,
        "duplicate_audit": duplicate_audit,
    }
    return DatasetBundle(
        train=normalized["train"],
        validation=normalized["validation"],
        test=normalized["test"],
        labels=labels,
        manifest=manifest,
    )
