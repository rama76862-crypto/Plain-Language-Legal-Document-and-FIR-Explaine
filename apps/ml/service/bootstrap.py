"""Build the production pipeline from local, trusted Backend 2 artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path

from apps.ml.service.contracts import ReferenceRecord
from apps.ml.service.pipeline import AnalysisPipeline

ML_DIR = Path(__file__).resolve().parents[1]


def build_default_pipeline() -> AnalysisPipeline | None:
    """Load optional local artifacts; missing models leave health degraded."""
    try:
        from apps.ml.inference.generator import LocalGenerator
        from apps.ml.retrieval.document_index import build_document_index
        from apps.ml.retrieval.reference_index import find_official_references
        from apps.ml.training.model import UnfairToSClassifier
        from apps.ml.translation.local_translator import LocalTranslator
        from apps.ml.validation.agreement_rules import agreement_attention_items
        from apps.ml.validation.result_validator import validate_analysis_result, validate_question_answer
    except ImportError:
        return None

    classifier = None
    artifact_dir = Path(os.environ.get("ML_CLASSIFIER_DIR", ML_DIR / "training" / "artifacts"))
    try:
        classifier = UnfairToSClassifier.load(artifact_dir)
    except (FileNotFoundError, OSError, ValueError, ImportError):
        classifier = None

    base_url = os.environ.get("ML_LLM_BASE_URL", "http://127.0.0.1:8080")
    try:
        from apps.ml.inference.artifacts import MODEL_NAME

        generator = LocalGenerator(
            base_url=base_url,
            model_name=os.environ.get("ML_LLM_MODEL_NAME", MODEL_NAME),
            timeout_seconds=float(os.environ.get("MODEL_TIMEOUT_SECONDS", "180")),
        )
        translator = LocalTranslator(generator)
    except (ValueError, OSError):
        generator = None
        translator = None

    tested_languages = {"en": False, "hi": False, "pa": False}
    language_matrix_path = ML_DIR / "data" / "language-evaluation.json"
    if language_matrix_path.exists():
        try:
            matrix = json.loads(language_matrix_path.read_text(encoding="utf-8"))
            tested_languages.update({key: bool(matrix.get(key, False)) for key in tested_languages})
        except (OSError, json.JSONDecodeError):
            pass

    curated_references = ()
    references_path = ML_DIR / "data" / "references.json"
    if references_path.exists():
        try:
            from apps.ml.retrieval.reference_index import CuratedReference

            reference_payload = json.loads(references_path.read_text(encoding="utf-8"))
            curated_references = tuple(
                CuratedReference(
                    record=ReferenceRecord.model_validate(entry["record"]),
                    law=entry.get("law"),
                )
                for entry in reference_payload
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            curated_references = ()

    return AnalysisPipeline(
        classifier=classifier,
        generator=generator,
        translator=translator,
        document_index_factory=build_document_index,
        agreement_attention_items=agreement_attention_items,
        validate_analysis_result=validate_analysis_result,
        validate_question_answer=validate_question_answer,
        references=curated_references,
        find_official_references=find_official_references,
        tested_languages=tested_languages,
    )

