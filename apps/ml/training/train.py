"""Command-line entry point: ``python -m apps.ml.training.train``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import DEFAULT_CACHE_DIR, load_lexglue_unfair_tos
from .model import DEFAULT_ARTIFACT_DIR, train_baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CPU UNFAIR-ToS word/character TF-IDF baseline.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Ignored local Hugging Face cache directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACT_DIR, help="Locally generated classifier artifacts")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    bundle = load_lexglue_unfair_tos(args.cache_dir)
    print(
        "Loaded pinned LexGLUE UNFAIR-ToS splits: "
        + json.dumps(bundle.manifest["split_counts"], sort_keys=True),
        flush=True,
    )
    result = train_baseline(bundle, args.output_dir, random_seed=args.seed)
    test = result["metrics"]["held_out_test"]
    print(f"Classifier: {result['metadata']['classifier_version']}", flush=True)
    print(
        "Held-out test metrics (single evaluation): "
        + json.dumps({"macro_f1": test["macro_f1"], "micro_f1": test["micro_f1"], "examples": test["examples"]}, sort_keys=True),
        flush=True,
    )
    print(f"Artifacts: {result['artifact_dir']}", flush=True)


if __name__ == "__main__":
    main()
