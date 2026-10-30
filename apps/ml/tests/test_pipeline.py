"""Pipeline routing uses labelled synthetic fixtures and an explicit fake generator."""

from __future__ import annotations

import asyncio
import json

from apps.ml.retrieval.document_index import build_document_index
from apps.ml.service.contracts import (
    AnalysisProgress,
    AnalysisRequest,
    ClassifierPrediction,
    ClassifierResult,
    ClauseInput,
    Evidence,
    GenerationRequest,
    GenerationResult,
    QuestionRequest,
)
from apps.ml.service.pipeline import AnalysisPipeline
from apps.ml.validation.agreement_rules import agreement_attention_items
from apps.ml.validation.result_validator import validate_analysis_result, validate_question_answer


class FixtureClassifier:
    classifier_version = "fixture-classifier-v1"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def predict(self, text: str) -> ClassifierResult:
        self.calls.append(text)
        return ClassifierResult(
            classifier_version=self.classifier_version,
            predictions=[
                ClassifierPrediction(
                    label="unilateral_change",
                    score=0.91,
                    threshold=0.5,
                    detected=True,
                )
            ],
        )


class FixtureGenerator:
    model_name = "fixture-generator"

    def __init__(self) -> None:
        self.calls = 0

    async def health(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        payload = json.loads(request.user_prompt)
        if "clause_id" not in payload:
            return GenerationResult(
                text=json.dumps(
                    {
                        "summary": "The reviewed clause states a monthly fee of INR 1500.",
                        "reference_ids": [],
                        "limitations": [],
                    }
                ),
                model=self.model_name,
                latency_ms=1.0,
                output_tokens=10,
            )
        clause_id = payload["clause_id"]
        source = payload["original_reviewed_text_window"]
        document_type = payload["document_type"]
        if document_type == "fir":
            summary = "The FIR records an allegation stated in the complaint."
            facts = [
                {
                    "category": "allegation",
                    "value": "The complaint alleges that the person took a bag.",
                }
            ]
        elif document_type == "notice":
            summary = "The notice asks for the stated action and gives a relative response period."
            facts = [
                {
                    "category": "requested_action",
                    "value": "The notice asks the recipient to take the stated action.",
                }
            ]
        else:
            summary = "This clause states how the agreement operates."
            facts = []
        attention = [
            {
                "category": candidate["category"],
                "explanation": "This wording matches a configured review cue.",
            }
            for candidate in payload["attention_candidates"]
        ]
        content = json.dumps(
            {
                "summary": summary,
                "attention": attention,
                "facts": facts,
                "reference_ids": [],
                "limitations": ["synthetic fixture output"],
            }
        )
        return GenerationResult(
            text=content,
            model=self.model_name,
            latency_ms=1.0,
            output_tokens=10,
        )


class NeedsReviewTranslator:
    async def translate(self, clause: ClauseInput, source_language: str):
        from apps.ml.service.contracts import TranslationResult

        return TranslationResult(
            clause_id=clause.clause_id,
            original_text=clause.reviewed_text,
            source_language=source_language,
            pivot_text=None,
            review_status="needs_review",
            checks=["synthetic_fluent_review_missing"],
        )


class FabricatedQuoteGenerator(FixtureGenerator):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        return GenerationResult(
            text=json.dumps(
                {
                    "summary": "This synthetic record is explained.",
                    "evidence": [
                        {
                            "clause_id": "unknown-clause-id",
                            "quote": "fabricated quote not in the reviewed source",
                        }
                    ],
                }
            ),
            model=self.model_name,
            latency_ms=1.0,
            output_tokens=10,
        )


class InvalidQuestionOnceGenerator(FixtureGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.invalid_question_once = False

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.user_prompt.startswith("Repair this candidate once"):
            self.calls += 1
            return GenerationResult(
                text=json.dumps(
                    {"summary": "The synthetic monthly fee is INR 1500.", "reference_ids": [], "limitations": []}
                ),
                model=self.model_name,
                latency_ms=1.0,
                output_tokens=10,
            )
        payload = json.loads(request.user_prompt)
        if "clause_id" not in payload and not self.invalid_question_once:
            self.calls += 1
            self.invalid_question_once = True
            return GenerationResult(
                text="not-json",
                model=self.model_name,
                latency_ms=1.0,
                output_tokens=1,
            )
        return await super().generate(request)


def _pipeline() -> tuple[AnalysisPipeline, FixtureClassifier, FixtureGenerator]:
    classifier = FixtureClassifier()
    generator = FixtureGenerator()
    pipeline = AnalysisPipeline(
        classifier=classifier,
        generator=generator,
        translator=NeedsReviewTranslator(),
        document_index_factory=build_document_index,
        agreement_attention_items=agreement_attention_items,
        validate_analysis_result=validate_analysis_result,
        validate_question_answer=validate_question_answer,
    )
    return pipeline, classifier, generator


def _request(
    document_type: str,
    clause_id: str,
    text: str,
    *,
    input_language: str = "en",
) -> AnalysisRequest:
    return AnalysisRequest(
        document_id=f"synthetic-{document_type}-document",
        analysis_id=f"synthetic-{document_type}-analysis",
        document_revision=1,
        document_type=document_type,
        input_language=input_language,
        output_language="en",
        clauses=[ClauseInput(clause_id=clause_id, reviewed_text=text)],
    )


async def _analyze(pipeline: AnalysisPipeline, request: AnalysisRequest):
    progress: list[AnalysisProgress] = []

    async def record(value: AnalysisProgress) -> None:
        progress.append(value)

    result = await pipeline.analyze(request, record)
    return result, progress


def test_agreement_runs_cpu_classifier_rules_and_validated_local_schema() -> None:
    pipeline, classifier, generator = _pipeline()
    text = (
        "This synthetic agreement renews automatically each month unless cancelled. "
        "The provider may change these terms at any time without prior notice."
    )
    request = _request("agreement", "agreement-clause-1", text)

    result, progress = asyncio.run(_analyze(pipeline, request))

    assert result.coverage.analysed == 1
    assert result.provenance.classifier_version == "fixture-classifier-v1"
    assert classifier.calls and set(classifier.calls) == {text}
    assert len(classifier.calls) == 3  # one routing pass plus scores for the two emitted cues
    assert generator.calls == 1
    attention = {item.category: item for item in result.items if item.kind == "attention"}
    assert attention["unilateral_change"].detector == "rule"
    assert attention["automatic_renewal"].detector == "rule"
    assert all(item.evidence[0].quote == text for item in result.items)
    assert all(item.review_status == "needs_review" for item in result.items)
    assert all(
        "semantic_entailment_not_independently_verified" in item.limitations
        for item in result.items
    )
    assert any(item.stage == "generating" for item in progress)
    assert result.warnings == [
        "Generated explanations passed schema and source-evidence checks, but semantic entailment has not been independently reviewed."
    ]


def test_fir_bypasses_classifier_and_retains_allegation_wording() -> None:
    pipeline, classifier, _ = _pipeline()
    text = "The FIR records that the complainant alleges the person took a red bag."
    request = _request("fir", "fir-clause-1", text)

    result, _ = asyncio.run(_analyze(pipeline, request))

    assert classifier.calls == []
    assert result.coverage.analysed == 1
    assert all(item.kind == "allegation" for item in result.items)
    assert any("allegation" in item.explanation.casefold() for item in result.items)


def test_notice_extracts_action_and_keeps_receipt_relative_period_unresolved() -> None:
    pipeline, classifier, _ = _pipeline()
    text = "Notice: Pay the stated sum within 15 days of receipt."
    request = _request("notice", "notice-clause-1", text)

    result, _ = asyncio.run(_analyze(pipeline, request))

    assert classifier.calls == []
    assert result.coverage.analysed == 1
    assert any(item.kind == "notice_action" for item in result.items)
    assert len(result.deadlines) == 1
    deadline = result.deadlines[0]
    assert deadline.source_quote == "within 15 days of receipt"
    assert deadline.resolved_date is None
    assert deadline.status == "needs_information"
    assert deadline.missing_information == ["receipt_date"]


def test_other_document_does_not_use_agreement_classifier_and_unverified_law_is_not_cited() -> None:
    pipeline, classifier, _ = _pipeline()
    text = "This synthetic record mentions Section 420 IPC but supplies no official source."
    request = _request("other", "other-clause-1", text)

    result, _ = asyncio.run(_analyze(pipeline, request))

    assert classifier.calls == []
    assert all(item.kind == "explanation" for item in result.items)
    assert result.references == []
    assert any("not matched to an exact curated authority" in warning for warning in result.warnings)


def test_hindi_clause_without_fluent_review_is_preserved_and_marked_for_review() -> None:
    pipeline, classifier, generator = _pipeline()
    text = "धारा ३०२ IPC के तहत आरोप दर्ज है।"
    request = _request("agreement", "hindi-clause-1", text, input_language="hi")

    result, _ = asyncio.run(_analyze(pipeline, request))

    assert classifier.calls == []
    assert generator.calls == 0
    assert result.coverage.analysed == 0
    assert [item.model_dump() for item in result.failed_clauses] == [
        {"clause_id": "hindi-clause-1", "reason": "translation_uncertain"}
    ]
    assert result.items[0].category == "translation_uncertain"
    assert result.items[0].review_status == "needs_review"
    assert result.items[0].evidence[0].quote == text


def test_unrelated_question_returns_insufficient_evidence_without_generation() -> None:
    pipeline, _, generator = _pipeline()
    request = _request(
        "agreement",
        "agreement-clause-2",
        "The provider may change this agreement without prior notice.",
    )
    result, _ = asyncio.run(_analyze(pipeline, request))
    question = QuestionRequest(
        document_id=request.document_id,
        analysis_id=request.analysis_id,
        document_revision=request.document_revision,
        question="What is the weather on Jupiter?",
        output_language="en",
        client_request_id="synthetic-unsupported-question-1",
    )
    calls_after_analysis = generator.calls

    answer = asyncio.run(pipeline.answer(question, request, result))

    assert answer.review_status == "needs_review"
    assert "insufficient_evidence" in answer.limitations
    assert answer.evidence == []
    assert generator.calls == calls_after_analysis


def test_question_cleanup_closes_temporary_document_index() -> None:
    pipeline, _, _ = _pipeline()

    class TemporaryIndex:
        closed = False

        def search(self, query: str, *, limit: int = 5):
            return []

        def close(self) -> None:
            self.closed = True

    temporary_index = TemporaryIndex()
    pipeline.document_index_factory = lambda clauses: temporary_index
    request = _request("agreement", "agreement-clause-cleanup", "A synthetic reviewed clause.")
    result, _ = asyncio.run(_analyze(pipeline, request))
    question = QuestionRequest(
        document_id=request.document_id,
        analysis_id=request.analysis_id,
        document_revision=request.document_revision,
        question="What is the weather on Jupiter?",
        output_language="en",
        client_request_id="synthetic-cleanup-question",
    )

    answer = asyncio.run(pipeline.answer(question, request, result))

    assert answer.review_status == "needs_review"
    assert temporary_index.closed


def test_generated_question_answer_stays_needs_review_without_semantic_review() -> None:
    pipeline, _, _ = _pipeline()
    text = "The synthetic monthly fee is INR 1500 and is due on the fifth day of each month."
    request = _request("agreement", "agreement-question-review", text)
    result, _ = asyncio.run(_analyze(pipeline, request))
    question = QuestionRequest(
        document_id=request.document_id,
        analysis_id=request.analysis_id,
        document_revision=request.document_revision,
        question="What is the monthly fee?",
        output_language="en",
        client_request_id="synthetic-question-review-status",
    )

    answer = asyncio.run(pipeline.answer(question, request, result))

    assert answer.review_status == "needs_review"
    assert "semantic_entailment_not_independently_verified" in answer.limitations
    assert answer.evidence == [Evidence(clause_id=request.clauses[0].clause_id, quote=text)]


def test_generated_question_output_gets_one_repair_attempt_then_marks_review() -> None:
    generator = InvalidQuestionOnceGenerator()
    pipeline = AnalysisPipeline(
        classifier=FixtureClassifier(),
        generator=generator,
        translator=NeedsReviewTranslator(),
        document_index_factory=build_document_index,
        agreement_attention_items=agreement_attention_items,
        validate_analysis_result=validate_analysis_result,
        validate_question_answer=validate_question_answer,
    )
    text = "The synthetic monthly fee is INR 1500 and is due on the fifth day of each month."
    request = _request("agreement", "agreement-question-repair", text)
    result, _ = asyncio.run(_analyze(pipeline, request))
    question = QuestionRequest(
        document_id=request.document_id,
        analysis_id=request.analysis_id,
        document_revision=request.document_revision,
        question="What is the monthly fee?",
        output_language="en",
        client_request_id="synthetic-question-repair",
    )

    answer = asyncio.run(pipeline.answer(question, request, result))

    assert generator.calls == 3  # analysis, invalid question output, one repair
    assert answer.review_status == "needs_review"
    assert "question_output_repaired_once" in answer.limitations
    assert "semantic_entailment_not_independently_verified" in answer.limitations
    assert answer.evidence == [Evidence(clause_id=request.clauses[0].clause_id, quote=text)]


def test_model_supplied_fabricated_quote_and_clause_id_are_rejected() -> None:
    classifier = FixtureClassifier()
    generator = FabricatedQuoteGenerator()
    pipeline = AnalysisPipeline(
        classifier=classifier,
        generator=generator,
        translator=NeedsReviewTranslator(),
        document_index_factory=build_document_index,
        agreement_attention_items=agreement_attention_items,
        validate_analysis_result=validate_analysis_result,
        validate_question_answer=validate_question_answer,
    )
    text = "A synthetic record contains only the reviewed source text."
    request = _request("other", "other-clause-fabricated", text)

    result, _ = asyncio.run(_analyze(pipeline, request))

    assert result.coverage.analysed == 0
    assert [item.model_dump() for item in result.failed_clauses] == [
        {"clause_id": "other-clause-fabricated", "reason": "model_output_validation_failed"}
    ]
    assert result.items[0].category == "model_output_validation_failed"
    assert result.items[0].evidence[0].quote == text
    assert "fabricated quote" not in result.items[0].explanation
    assert any("unknown_model_evidence_clause" in warning for warning in result.warnings)
