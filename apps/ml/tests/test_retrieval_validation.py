"""Focused retrieval and evidence checks using labelled synthetic examples only."""

from __future__ import annotations

from datetime import date

import pytest

from apps.ml.retrieval import (
    CuratedReference,
    LocalDocumentIndex,
    find_official_references,
)
from apps.ml.service.contracts import (
    AnalysisItem,
    AnalysisRequest,
    AnalysisResult,
    ClauseInput,
    Coverage,
    Deadline,
    Evidence,
    QuestionAnswer,
    QuestionRequest,
    ReferenceRecord,
)
from apps.ml.validation import (
    agreement_attention_items,
    validate_analysis_result,
    validate_question_answer,
)


SYNTHETIC_CLAUSE = ClauseInput(
    clause_id="synthetic-clause-1",
    reviewed_text=(
        "This synthetic subscription automatically renews each month unless "
        "cancelled at least 30 days before term end."
    ),
    source_ref={"page_number": 1},
)
SYNTHETIC_DEADLINE_CLAUSE = ClauseInput(
    clause_id="synthetic-clause-2",
    reviewed_text="Pay within 15 days of receipt; no receipt date is recorded in this synthetic clause.",
)


def _request(*, document_type: str = "agreement", clauses=None) -> AnalysisRequest:
    return AnalysisRequest(
        document_id="synthetic-document-1",
        analysis_id="synthetic-analysis-1",
        document_revision=1,
        document_type=document_type,
        input_language="en",
        output_language="en",
        clauses=list(clauses or [SYNTHETIC_CLAUSE]),
    )


def _item(
    *,
    clause_id: str = SYNTHETIC_CLAUSE.clause_id,
    quote: str = "automatically renews",
    explanation: str = "This wording describes automatic renewal.",
    reference_ids: list[str] | None = None,
    kind: str = "attention",
    detector: str = "rule",
) -> AnalysisItem:
    return AnalysisItem(
        item_id="synthetic-item-1",
        clause_id=clause_id,
        kind=kind,
        category="automatic_renewal",
        explanation=explanation,
        evidence=[Evidence(clause_id=clause_id, quote=quote)],
        reference_ids=reference_ids or [],
        review_status="supported",
        detector=detector,
    )


def _result(
    request: AnalysisRequest,
    *,
    item: AnalysisItem | None = None,
    deadlines: list[Deadline] | None = None,
    coverage: Coverage | None = None,
    references: list[ReferenceRecord] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        document_id=request.document_id,
        analysis_id=request.analysis_id,
        document_revision=request.document_revision,
        input_language=request.input_language,
        output_language=request.output_language,
        document_type=request.document_type,
        coverage=coverage or Coverage(analysed=len(request.clauses), total=len(request.clauses)),
        items=[item] if item is not None else [],
        deadlines=deadlines or [],
        references=references or [],
    )


def _synthetic_reference() -> CuratedReference:
    """A synthetic-only record; it is not a legal authority or production citation."""
    return CuratedReference(
        law="Synthetic fixture law",
        record=ReferenceRecord(
            reference_id="synthetic-reference-1",
            title="Synthetic fixture reference",
            url="https://example.test/synthetic-reference",
            section="TEST-SECTION-1",
            version="fixture-v1",
            jurisdiction="IN",
            excerpt="Synthetic test excerpt only; not legal content or legal authority.",
        ),
    )


def test_document_index_ranks_only_reviewed_clauses_and_can_be_cleared() -> None:
    other = ClauseInput(
        clause_id="synthetic-clause-3",
        reviewed_text="The synthetic notice asks for a response by a stated date.",
    )
    index = LocalDocumentIndex([SYNTHETIC_CLAUSE, other])

    hits = index.search("automatic subscription renewal", limit=2)

    assert hits
    assert hits[0].record_id == SYNTHETIC_CLAUSE.clause_id
    assert hits[0].text == SYNTHETIC_CLAUSE.reviewed_text
    assert hits[0].source_kind == "document"
    assert index.search("unrelated missing phrase") == []
    index.close()
    assert index.search("automatic renewal") == []


def test_document_index_tokenizes_indic_text_without_hosted_dependencies() -> None:
    clause = ClauseInput(clause_id="synthetic-hi-1", reviewed_text="किराया हर महीने देना होगा।")

    hits = LocalDocumentIndex([clause]).search("किराया")

    assert len(hits) == 1
    assert hits[0].record_id == "synthetic-hi-1"


def test_official_lookup_filters_metadata_and_marks_exact_section() -> None:
    exact = _synthetic_reference()
    wrong_version = CuratedReference(
        law=exact.law,
        record=exact.record.model_copy(update={"reference_id": "synthetic-reference-old", "version": "fixture-v0"}),
    )

    matches = find_official_references(
        [exact, wrong_version],
        "synthetic section lookup",
        section="test-section-1",
        law="SYNTHETIC FIXTURE LAW",
        jurisdiction="in",
        version="fixture-v1",
    )

    assert len(matches) == 1
    assert matches[0].hit.record_id == "synthetic-reference-1"
    assert matches[0].hit.source_kind == "official_reference"
    assert matches[0].exact_section_match is True


def test_official_semantic_matches_are_candidates_not_exact_section_matches() -> None:
    reference = _synthetic_reference()

    matches = find_official_references(
        [reference],
        "synthetic excerpt authority",
        section="missing-section",
        law=reference.law,
        jurisdiction="IN",
        version="fixture-v1",
    )

    assert matches
    assert matches[0].exact_section_match is False


@pytest.mark.parametrize(
    "text,category",
    [
        (
            "The synthetic subscription automatically renews unless cancelled 30 days before term end.",
            "automatic_renewal",
        ),
        ("A synthetic late payment fee applies only after the cure period.", "payment_penalty"),
        ("A synthetic prepayment penalty applies only if the balance is cleared early.", "payment_penalty"),
    ],
)
def test_agreement_attention_rules_detect_positive_cues_with_opt_outs(text: str, category: str) -> None:
    clause = ClauseInput(clause_id="synthetic-rule-1", reviewed_text=text)

    items = agreement_attention_items(clause)

    assert len(items) == 1
    assert items[0].category == category
    assert items[0].detector == "rule"
    assert items[0].evidence[0].quote in clause.reviewed_text


@pytest.mark.parametrize(
    "text",
    [
        "This synthetic agreement does not automatically renew.",
        "The automatic renewal provision is excluded from this synthetic agreement.",
        "No late payment penalty applies under this synthetic clause.",
        "A late payment fee will not be charged under this synthetic clause.",
    ],
)
def test_agreement_attention_rules_skip_direct_negations_and_exceptions(text: str) -> None:
    clause = ClauseInput(clause_id="synthetic-rule-negative", reviewed_text=text)

    assert agreement_attention_items(clause) == []


def test_agreement_attention_rules_skip_non_agreement_documents() -> None:
    clause = ClauseInput(
        clause_id="synthetic-fir-1",
        reviewed_text="The synthetic subscription automatically renews every month.",
    )

    assert agreement_attention_items(clause, document_type="fir") == []


def test_result_validation_accepts_exact_reviewed_quote_and_receipt_deadline() -> None:
    request = _request(clauses=[SYNTHETIC_DEADLINE_CLAUSE])
    deadline = Deadline(
        deadline_id="synthetic-deadline-1",
        clause_id=SYNTHETIC_DEADLINE_CLAUSE.clause_id,
        source_quote="within 15 days of receipt",
        display_text="15 days after receipt",
        anchor="receipt",
        resolved_date=None,
        status="needs_information",
        missing_information=["receipt_date"],
    )
    result = _result(request, deadlines=[deadline])

    report = validate_analysis_result(result, request)

    assert report.valid is True
    assert report.issues == []


def test_result_validation_rejects_fabricated_quote_and_unknown_clause_id() -> None:
    request = _request()
    unknown_item = _item(
        clause_id="synthetic-clause-missing",
        quote="automatically renews",
    )
    fabricated_quote_item = _item(quote="invented synthetic text").model_copy(
        update={"item_id": "synthetic-item-fabricated-quote"}
    )
    result = _result(request, item=unknown_item).model_copy(
        update={"items": [unknown_item, fabricated_quote_item]}
    )

    report = validate_analysis_result(result, request)

    codes = {issue.code for issue in report.issues}
    assert report.valid is False
    assert "unknown_clause_id" in codes
    assert "quote_not_in_reviewed_text" in codes


def test_result_validation_rejects_unknown_reference_ids() -> None:
    request = _request()
    item = _item(reference_ids=["not-in-curated-test-data"])

    report = validate_analysis_result(_result(request, item=item), request)

    assert report.valid is False
    assert "unknown_reference_id" in {issue.code for issue in report.issues}


def test_result_validation_rejects_untrusted_reference_record_even_if_well_formed() -> None:
    request = _request()
    invented = _synthetic_reference().record.model_copy(
        update={"reference_id": "invented-result-reference"}
    )

    report = validate_analysis_result(_result(request, references=[invented]), request)

    assert report.valid is False
    assert "unknown_reference_record" in {issue.code for issue in report.issues}


def test_result_validation_rejects_unsupported_amount_or_date_literals() -> None:
    request = _request()
    item = _item(
        quote="automatically renews",
        explanation="This clause adds a $500 payment due on 2030-01-02.",
    )

    report = validate_analysis_result(_result(request, item=item), request)

    assert report.valid is False
    assert "unsupported_critical_literal" in {issue.code for issue in report.issues}


def test_result_validation_rejects_changed_code_identifier_for_same_section_number() -> None:
    clause = ClauseInput(
        clause_id="synthetic-identifier-clause",
        reviewed_text="This synthetic text refers to IPC Section 302.",
    )
    request = _request(clauses=[clause])
    item = _item(
        clause_id=clause.clause_id,
        quote=clause.reviewed_text,
        explanation="This synthetic text refers to BNS Section 302.",
    )

    report = validate_analysis_result(_result(request, item=item), request)

    assert report.valid is False
    assert "unsupported_critical_literal" in {issue.code for issue in report.issues}


def test_result_validation_accepts_preserved_amount_date_and_code_across_date_formatting() -> None:
    clause = ClauseInput(
        clause_id="synthetic-critical-values",
        reviewed_text="Pay ₹1,500 by 15/03/2025 under IPC Section 302.",
    )
    request = _request(clauses=[clause])
    item = _item(
        clause_id=clause.clause_id,
        quote=clause.reviewed_text,
        explanation="Pay INR 1500 by March 15, 2025 under IPC Section 302.",
    )

    report = validate_analysis_result(_result(request, item=item), request)

    assert report.valid is True
    assert report.issues == []


def test_result_validation_requires_receipt_date_to_remain_unresolved() -> None:
    request = _request(clauses=[SYNTHETIC_DEADLINE_CLAUSE])
    deadline = Deadline(
        deadline_id="synthetic-deadline-invalid",
        clause_id=SYNTHETIC_DEADLINE_CLAUSE.clause_id,
        source_quote="within 15 days of receipt",
        display_text="A date will be determined after receipt",
        anchor="receipt",
        resolved_date=date(2029, 2, 28),
        status="explicit",
        missing_information=[],
    )

    report = validate_analysis_result(_result(request, deadlines=[deadline]), request)

    codes = {issue.code for issue in report.issues}
    assert report.valid is False
    assert "receipt_deadline_resolved_without_anchor" in codes
    assert "receipt_date_not_marked_missing" in codes
    assert "receipt_deadline_status_invalid" in codes


def test_result_validation_binds_document_and_revision() -> None:
    request = _request()
    result = _result(request).model_copy(update={"document_revision": 2})

    report = validate_analysis_result(result, request)

    assert report.valid is False
    assert "document_revision_mismatch" in {issue.code for issue in report.issues}


def test_fir_result_requires_allegation_language_and_bypasses_classifier() -> None:
    clause = ClauseInput(
        clause_id="synthetic-fir-clause",
        reviewed_text="The synthetic complaint says the person took a red bag.",
    )
    request = _request(document_type="fir", clauses=[clause])
    grounded_item = AnalysisItem(
        item_id="synthetic-fir-item",
        clause_id=clause.clause_id,
        kind="allegation",
        category="recorded_allegation",
        explanation="The FIR records an allegation that a person took a red bag.",
        evidence=[Evidence(clause_id=clause.clause_id, quote=clause.reviewed_text)],
        detector="extraction",
    )
    assert validate_analysis_result(_result(request, item=grounded_item), request).valid

    overclaim = grounded_item.model_copy(
        update={"explanation": "The person took a red bag.", "detector": "classifier"}
    )
    report = validate_analysis_result(_result(request, item=overclaim), request)

    codes = {issue.code for issue in report.issues}
    assert report.valid is False
    assert "fir_allegation_framing_missing" in codes
    assert "fir_classifier_bypass_violation" in codes


def test_question_answer_is_bound_to_current_analysis_and_exact_evidence() -> None:
    analysis_request = _request()
    question_request = QuestionRequest(
        document_id=analysis_request.document_id,
        analysis_id=analysis_request.analysis_id,
        document_revision=analysis_request.document_revision,
        question="What renews automatically?",
        output_language=analysis_request.output_language,
        client_request_id="synthetic-question-request-1",
    )
    answer = QuestionAnswer(
        answer="The synthetic subscription renews automatically.",
        evidence=[Evidence(clause_id=SYNTHETIC_CLAUSE.clause_id, quote="automatically renews")],
    )

    report = validate_question_answer(answer, question_request, analysis_request)

    assert report.valid is True


def test_question_answer_rejects_stale_revision_and_fabricated_quote() -> None:
    analysis_request = _request()
    stale_question = QuestionRequest(
        document_id=analysis_request.document_id,
        analysis_id=analysis_request.analysis_id,
        document_revision=analysis_request.document_revision + 1,
        question="What is the period?",
        output_language=analysis_request.output_language,
        client_request_id="synthetic-question-request-stale",
    )
    answer = QuestionAnswer(
        answer="A synthetic period applies.",
        evidence=[Evidence(clause_id=SYNTHETIC_CLAUSE.clause_id, quote="fabricated quote")],
    )

    report = validate_question_answer(answer, stale_question, analysis_request)

    codes = {issue.code for issue in report.issues}
    assert report.valid is False
    assert "question_document_revision_mismatch" in codes
    assert "quote_not_in_reviewed_text" in codes

