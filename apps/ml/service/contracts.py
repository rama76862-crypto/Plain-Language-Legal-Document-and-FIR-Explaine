"""Typed private-service and Contract v1 payloads.

The public API remains owned by Backend 1. These types are shared by the
classifier, local generator, retrieval, validation, and private service.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Language = Literal["en", "hi", "pa", "unknown"]
DocumentType = Literal["agreement", "fir", "notice", "other"]
AnalysisStatus = Literal["queued", "running", "complete", "needs_review", "failed"]
ResultKind = Literal["explanation", "attention", "allegation", "notice_action"]
ReviewStatus = Literal["supported", "needs_review"]
DeadlineStatus = Literal["explicit", "needs_information", "needs_review"]
Detector = Literal["rule", "classifier", "model", "extraction"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SourceRef(StrictModel):
    page_number: int | None = Field(default=None, ge=1)
    paragraph_index: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None


class ClauseInput(StrictModel):
    clause_id: str = Field(min_length=1)
    reviewed_text: str = Field(min_length=1)
    source_ref: SourceRef | None = None


class AnalysisRequest(StrictModel):
    document_id: str = Field(min_length=1)
    analysis_id: str = Field(min_length=1)
    document_revision: int = Field(ge=1)
    document_type: DocumentType
    input_language: Language
    output_language: Language
    clauses: list[ClauseInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_clause_ids(self) -> "AnalysisRequest":
        ids = [clause.clause_id for clause in self.clauses]
        if len(ids) != len(set(ids)):
            raise ValueError("clause_id values must be unique within an analysis")
        return self


class Evidence(StrictModel):
    clause_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class AnalysisItem(StrictModel):
    item_id: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    kind: ResultKind
    category: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = "supported"
    detector: Detector
    model_score: float | None = Field(default=None, ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)


class Deadline(StrictModel):
    deadline_id: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    display_text: str = Field(min_length=1)
    anchor: str | None = None
    resolved_date: date | None = None
    status: DeadlineStatus
    missing_information: list[str] = Field(default_factory=list)


class ReferenceRecord(StrictModel):
    reference_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    section: str | None = None
    version: str | None = None
    jurisdiction: str = Field(default="IN")
    excerpt: str = Field(min_length=1)


class Coverage(StrictModel):
    analysed: int = Field(ge=0)
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def analysed_not_over_total(self) -> "Coverage":
        if self.analysed > self.total:
            raise ValueError("analysed coverage cannot exceed total")
        return self


class Provenance(StrictModel):
    classifier_version: str | None = None
    generator: str | None = None
    rules_version: str | None = None


class AnalysisResult(StrictModel):
    document_id: str
    analysis_id: str
    document_revision: int = Field(ge=1)
    input_language: Language
    output_language: Language
    document_type: DocumentType
    coverage: Coverage
    items: list[AnalysisItem] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    legal_aid: list[dict[str, str]] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)
    references: list[ReferenceRecord] = Field(default_factory=list)


class AnalysisProgress(StrictModel):
    completed_clauses: int = Field(ge=0)
    total_clauses: int = Field(ge=0)
    stage: str | None = None
    failed_clauses: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def progress_bounds(self) -> "AnalysisProgress":
        if self.completed_clauses > self.total_clauses:
            raise ValueError("completed_clauses cannot exceed total_clauses")
        if self.failed_clauses > self.completed_clauses:
            raise ValueError("failed_clauses cannot exceed completed_clauses")
        return self


class JobSnapshot(StrictModel):
    analysis_id: str
    status: AnalysisStatus
    progress: AnalysisProgress
    document_revision: int = Field(ge=1)
    output_language: Language
    result: AnalysisResult | None = None
    warnings: list[str] = Field(default_factory=list)


class QuestionRequest(StrictModel):
    document_id: str = Field(min_length=1)
    analysis_id: str = Field(min_length=1)
    document_revision: int = Field(ge=1)
    question: str = Field(min_length=1, max_length=2000)
    output_language: Language
    client_request_id: str = Field(min_length=1)


class QuestionAnswer(StrictModel):
    answer: str = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = "supported"
    limitations: list[str] = Field(default_factory=list)


class ClassifierPrediction(StrictModel):
    label: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    detected: bool


class ClassifierResult(StrictModel):
    predictions: list[ClassifierPrediction] = Field(default_factory=list)
    classifier_version: str = Field(min_length=1)


class TranslationResult(StrictModel):
    clause_id: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    source_language: Language
    pivot_text: str | None = None
    model: str | None = None
    version: str | None = None
    review_status: ReviewStatus
    checks: list[str] = Field(default_factory=list)


class GenerationRequest(StrictModel):
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    response_schema: dict[str, Any] | None = None
    max_new_tokens: int = Field(default=384, ge=1, le=2048)


class GenerationResult(StrictModel):
    text: str = Field(min_length=1)
    model: str = Field(min_length=1)
    latency_ms: float = Field(ge=0.0)
    output_tokens: int | None = Field(default=None, ge=0)


class RetrievalHit(StrictModel):
    record_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    score: float
    source_kind: Literal["document", "official_reference"]
    reference: ReferenceRecord | None = None


class ValidationIssue(StrictModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    clause_id: str | None = None
    item_id: str | None = None


class ValidationReport(StrictModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class ServiceErrorBody(StrictModel):
    code: str
    message: str
    retryable: bool


class ServiceError(StrictModel):
    error: ServiceErrorBody
    request_id: str


def insufficient_evidence_answer(output_language: Language) -> QuestionAnswer:
    """Return a deterministic, honest response when no grounded answer exists."""
    messages = {
        "en": "The reviewed document and verified references do not contain enough information to answer this question.",
        "hi": "समीक्षित दस्तावेज़ और सत्यापित संदर्भों में इस प्रश्न का उत्तर देने के लिए पर्याप्त जानकारी नहीं है।",
        "pa": "ਸਮੀਖਿਆ ਕੀਤੇ ਦਸਤਾਵੇਜ਼ ਅਤੇ ਪ੍ਰਮਾਣਿਤ ਹਵਾਲਿਆਂ ਵਿੱਚ ਇਸ ਸਵਾਲ ਦਾ ਜਵਾਬ ਦੇਣ ਲਈ ਕਾਫ਼ੀ ਜਾਣਕਾਰੀ ਨਹੀਂ ਹੈ।",
        "unknown": "The reviewed document and verified references do not contain enough information to answer this question.",
    }
    return QuestionAnswer(
        answer=messages[output_language],
        review_status="needs_review",
        limitations=["insufficient_evidence"],
    )

