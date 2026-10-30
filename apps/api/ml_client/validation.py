"""Structural/evidence validation; semantic legal validation remains BE2's job."""
from typing import Any, Literal
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from apps.api.schemas import ApiError, DocumentType, Language, OutputLanguage


class Model(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True, allow_inf_nan=False)


class Evidence(Model):
    clause_id: str
    quote: str = Field(min_length=1)


class Item(Model):
    item_id: str
    clause_id: str
    kind: Literal['explanation', 'attention', 'allegation', 'notice_action']
    category: str | None
    explanation: str = Field(min_length=1)
    evidence: list[Evidence]
    reference_ids: list[str]
    review_status: Literal['supported', 'needs_review']
    detector: str
    model_score: float | int | None
    limitations: list[str]


class Deadline(Model):
    deadline_id: str
    clause_id: str
    source_quote: str = Field(min_length=1)
    display_text: str
    anchor: str | None
    resolved_date: str | None
    status: Literal['explicit', 'needs_information', 'needs_review']
    missing_information: list[str]


class Reference(Model):
    reference_id: str
    title: str
    url: str
    section: str | None
    version: str | None = None
    excerpt: str


class Coverage(Model):
    analysed: int = Field(ge=0)
    total: int = Field(ge=0)


class Provenance(Model):
    classifier_version: str
    generator: str
    rules_version: str


class LegalAid(Model):
    title: str
    url: str


class Result(Model):
    document_id: str
    analysis_id: str
    document_revision: int = Field(ge=1)
    input_language: Language
    output_language: OutputLanguage
    document_type: DocumentType
    coverage: Coverage
    items: list[Item]
    deadlines: list[Deadline]
    warnings: list[str]
    legal_aid: list[LegalAid]
    provenance: Provenance
    references: list[Reference] = Field(default_factory=list)


class Progress(Model):
    completed_clauses: int = Field(ge=0)
    total_clauses: int = Field(ge=0)


class Snapshot(Model):
    analysis_id: str
    status: Literal['queued', 'running', 'complete', 'needs_review', 'failed']
    document_revision: int = Field(ge=1)
    output_language: OutputLanguage
    progress: Progress
    result: Result | None = None
    warnings: list[str] = Field(default_factory=list)


class Answer(Model):
    answer: str = Field(min_length=1)
    evidence: list[Evidence]
    reference_ids: list[str]
    review_status: Literal['supported', 'needs_review']
    limitations: list[str]


def _invalid():
    # Never expose validation values: they may contain private document text.
    raise ApiError('INVALID_MODEL_OUTPUT', 'The local ML response failed contract or evidence checks.', 502)


def _clauses(payload: dict) -> dict[str, str]:
    clauses = payload.get('clauses', [])
    result = {}
    for clause in clauses:
        if hasattr(clause, 'model_dump'):
            clause = clause.model_dump()
        result[clause['clause_id']] = clause['reviewed_text']
    return result


def _evidence(evidence: list[Evidence], clauses: dict[str, str]):
    for ev in evidence:
        if ev.clause_id not in clauses or ev.quote not in clauses[ev.clause_id]:
            _invalid()


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ''
    return parsed.scheme == 'https' and not parsed.username and not parsed.password and (
        host.endswith('.gov.in') or host.endswith('.nic.in'))


def _failed_ids(data: dict, *, allow_progress_count: bool = False) -> set[str]:
    failed = data.get('failed_clauses', [])
    if allow_progress_count and isinstance(failed, int) and not isinstance(failed, bool):
        if failed < 0:
            _invalid()
        return set()
    if not isinstance(failed, list):
        _invalid()
    ids = []
    for entry in failed:
        if isinstance(entry, str):
            ids.append(entry)
        elif isinstance(entry, dict) and isinstance(entry.get('clause_id'), str):
            ids.append(entry['clause_id'])
        else:
            _invalid()
    if len(ids) != len(set(ids)):
        _invalid()
    return set(ids)


def validate_snapshot(snapshot: dict, payload: dict) -> dict:
    try:
        model = Snapshot.model_validate(snapshot)
        clauses = _clauses(payload)
        if (model.analysis_id != payload['analysis_id'] or
                model.document_revision != payload['document_revision'] or
                model.output_language != payload['output_language']):
            _invalid()
        if 'document_id' in snapshot and snapshot['document_id'] != payload['document_id']:
            _invalid()
        progress = model.progress
        if progress.total_clauses != len(clauses) or progress.completed_clauses > progress.total_clauses:
            _invalid()
        progress_data = snapshot.get('progress', {})
        progress_failed_count = progress_data.get('failed_clauses')
        if progress_failed_count is not None and (
                not isinstance(progress_failed_count, int) or isinstance(progress_failed_count, bool)
                or progress_failed_count < 0):
            _invalid()
        failed = _failed_ids(snapshot) | _failed_ids(progress_data, allow_progress_count=True)
        if not failed.issubset(clauses):
            _invalid()
        if model.status in {'complete', 'needs_review'} and model.result is None:
            # Terminal unusable content must identify every unanalysed clause.
            if model.status == 'complete' or not model.warnings or failed != set(clauses):
                _invalid()
        if model.status == 'complete' and (failed or progress.completed_clauses != len(clauses)):
            _invalid()
        if model.result is not None:
            result = model.result
            for key in ('document_id', 'analysis_id', 'document_revision', 'input_language', 'output_language', 'document_type'):
                if getattr(result, key) != payload[key]:
                    _invalid()
            if result.coverage.total != len(clauses) or result.coverage.analysed > result.coverage.total:
                _invalid()
            if result.coverage.analysed > progress.completed_clauses:
                _invalid()
            refs = {ref.reference_id for ref in result.references}
            if len(refs) != len(result.references) or any(not _official_url(ref.url) for ref in result.references):
                _invalid()
            if len({item.item_id for item in result.items}) != len(result.items):
                _invalid()
            covered = set()
            supported = set()
            for item in result.items:
                if item.clause_id not in clauses or not set(item.reference_ids).issubset(refs):
                    _invalid()
                if item.review_status == 'supported' and not item.evidence:
                    _invalid()
                _evidence(item.evidence, clauses)
                covered.add(item.clause_id)
                if item.review_status == 'supported':
                    supported.add(item.clause_id)
                if payload['document_type'] == 'fir' and item.kind == 'attention':
                    _invalid()
            failed |= _failed_ids(snapshot['result'])
            if not failed.issubset(clauses):
                _invalid()
            if progress_failed_count is not None and progress_failed_count != len(failed):
                _invalid()
            # A needs-review placeholder may represent a failed clause, but a supported
            # item cannot simultaneously claim that same clause failed analysis.
            if supported & failed:
                _invalid()
            analysed = covered - failed
            if result.coverage.analysed != len(analysed):
                _invalid()
            if len(covered | failed) > progress.completed_clauses:
                _invalid()
            # Warnings alone cannot account for missing clauses at a terminal state.
            if model.status in {'complete', 'needs_review', 'failed'} and (analysed | failed) != set(clauses):
                _invalid()
            if model.status == 'complete' and (result.coverage.analysed != len(clauses) or len(covered) != len(clauses) or failed):
                _invalid()
            if model.status == 'complete' and any(item.review_status == 'needs_review' for item in result.items):
                _invalid()
            for deadline in result.deadlines:
                if deadline.clause_id not in clauses or deadline.source_quote not in clauses[deadline.clause_id]:
                    _invalid()
                if deadline.status == 'needs_information' and (deadline.resolved_date is not None or not deadline.missing_information):
                    _invalid()
            for link in result.legal_aid:
                # v1 reviewed allowlist; adding other resources requires an agreed source list.
                if link.url.rstrip('/') != 'https://nalsa.gov.in/legal-aid':
                    _invalid()
        return model.model_dump(exclude_unset=True)
    except (ValidationError, KeyError, TypeError, ValueError, AttributeError):
        _invalid()


def validate_answer(answer: dict, payload: dict, result: dict) -> dict:
    try:
        model = Answer.model_validate(answer)
        for key in ('analysis_id', 'document_id', 'document_revision'):
            if result[key] != payload[key]:
                _invalid()
        clauses = _clauses(payload)
        _evidence(model.evidence, clauses)
        refs = {ref['reference_id'] for ref in result.get('references', [])}
        if not set(model.reference_ids).issubset(refs):
            _invalid()
        if model.review_status == 'supported' and not model.evidence:
            _invalid()
        # An unannounced answer.references extension must not bypass v1's reference scope.
        if answer.get('references'):
            _invalid()
        for key in ('analysis_id', 'document_id', 'document_revision', 'output_language'):
            if key in answer and answer[key] != payload[key]:
                _invalid()
        return model.model_dump(exclude_unset=True)
    except (ValidationError, KeyError, TypeError, ValueError, AttributeError):
        _invalid()
