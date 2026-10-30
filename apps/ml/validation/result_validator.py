"""Contract, membership, evidence, and conservative literal validation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

from pydantic import ValidationError as PydanticValidationError

from apps.ml.service.contracts import (
    AnalysisRequest,
    AnalysisResult,
    QuestionAnswer,
    QuestionRequest,
    ReferenceRecord,
    ValidationIssue,
    ValidationReport,
)

from apps.ml.retrieval.reference_index import CuratedReference

_Model = TypeVar("_Model", AnalysisResult, QuestionAnswer)
_DIGIT_TRANSLATION = {
    **{ord(chr(0x0966 + index)): str(index) for index in range(10)},
    **{ord(chr(0x0A66 + index)): str(index) for index in range(10)},
}
_NUMERIC_DATE = re.compile(r"\b(\d{1,4})\s*([./-])\s*(\d{1,2})\s*([./-])\s*(\d{1,4})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_MONTHS = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07",
    "july": "07", "aug": "08", "august": "08", "sep": "09",
    "sept": "09", "september": "09", "oct": "10", "october": "10",
    "nov": "11", "november": "11", "dec": "12", "december": "12",
}
for names in (
    "जनवरी फरवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर",
    "ਜਨਵਰੀ ਫਰਵਰੀ ਮਾਰਚ ਅਪ੍ਰੈਲ ਮਈ ਜੂਨ ਜੁਲਾਈ ਅਗਸਤ ਸਤੰਬਰ ਅਕਤੂਬਰ ਨਵੰਬਰ ਦਸੰਬਰ",
):
    _MONTHS.update({name:f"{index:02d}" for index,name in enumerate(names.split(),1)})
_MONTH_NAME_PATTERN = "|".join(sorted(_MONTHS, key=len, reverse=True))
_MONTH_FIRST_DATE = re.compile(
    rf"\b({_MONTH_NAME_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(\d{{4}})\b",
    re.IGNORECASE,
)
_DAY_FIRST_DATE = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_NAME_PATTERN})\.?[,]?\s+(\d{{4}})\b",
    re.IGNORECASE,
)
_AMOUNT = re.compile(
    r"(?ix)(?:₹|rs\.?|inr|usd|us\$|\$|€|eur|£|gbp)\s*"
    r"(?P<value>\d[\d,]*(?:\.\d+)?)"
    r"|\b(?P<value_words>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<currency_words>rupees?|inr|usd|dollars?|euros?|pounds?|रुपये|रुपया|रुपयों|ਰੁਪਏ|ਰੁਪਿਆ)(?![\w\u0900-\u097F\u0A00-\u0A7F])"
)
_PERCENT = re.compile(r"(?i)\b(\d[\d,]*(?:\.\d+)?)\s*(?:%|percent|प्रतिशत|ਫੀਸਦੀ|ਪ੍ਰਤੀਸ਼ਤ)(?!\w)")
_DURATION = re.compile(
    r"(?i)(?<!\w)(\d[\d,]*(?:\.\d+)?)[\s-]*("
    r"days?|weeks?|months?|years?|hours?|"
    r"दिनों|दिनो|दिन|"
    r"सप्ताहों|सप्ताह|हफ़्तों|हफ़्ते|हफ़्ता|हफ्तों|हफ्ते|हफ्ता|"
    r"महीनों|महीनो|महीने|महीना|मास|"
    r"वर्षों|वर्ष|सालों|सालो|साल|"
    r"घंटों|घंटो|घंटे|घंटा|घण्टों|घण्टे|घण्टा|"
    r"ਦਿਨਾਂ|ਦਿਨੋ|ਦਿਨ|"
    r"ਹਫ਼ਤਿਆਂ|ਹਫਤਿਆਂ|ਹਫ਼ਤੇ|ਹਫਤੇ|ਹਫ਼ਤਾ|ਹਫਤਾ|"
    r"ਮਹੀਨਿਆਂ|ਮਹੀਨੇ|ਮਹੀਨਾ|ਸਾਲਾਂ|ਸਾਲ|"
    r"ਘੰਟਿਆਂ|ਘੰਟੇ|ਘੰਟਾ)(?![\w\u0900-\u097F\u0A00-\u0A7F])"
)
_DURATION_UNIT = {
    "day": "day", "days": "day",
    "week": "week", "weeks": "week",
    "month": "month", "months": "month",
    "year": "year", "years": "year",
    "hour": "hour", "hours": "hour",
    "दिन": "day", "दिनों": "day", "दिनो": "day",
    "सप्ताह": "week", "सप्ताहों": "week", "हफ़्ता": "week", "हफ़्ते": "week", "हफ़्तों": "week",
    "हफ्ता": "week", "हफ्ते": "week", "हफ्तों": "week",
    "महीना": "month", "महीने": "month", "महीनों": "month", "महीनो": "month", "मास": "month",
    "वर्ष": "year", "वर्षों": "year", "साल": "year", "सालों": "year", "सालो": "year",
    "घंटा": "hour", "घंटे": "hour", "घंटों": "hour", "घंटो": "hour",
    "घण्टा": "hour", "घण्टे": "hour", "घण्टों": "hour",
    "ਦਿਨ": "day", "ਦਿਨਾਂ": "day", "ਦਿਨੋ": "day",
    "ਹਫ਼ਤਾ": "week", "ਹਫ਼ਤੇ": "week", "ਹਫ਼ਤਿਆਂ": "week",
    "ਹਫਤਾ": "week", "ਹਫਤੇ": "week", "ਹਫਤਿਆਂ": "week",
    "ਮਹੀਨਾ": "month", "ਮਹੀਨੇ": "month", "ਮਹੀਨਿਆਂ": "month",
    "ਸਾਲ": "year", "ਸਾਲਾਂ": "year",
    "ਘੰਟਾ": "hour", "ਘੰਟੇ": "hour", "ਘੰਟਿਆਂ": "hour",
}
_SECTION = re.compile(
    r"(?i)\b(section|sec\.?|article|art\.?|§|धारा|ਧਾਰਾ|अनुच्छेद|ਅਨੁਛੇਦ)\s*(?:no\.?\s*)?"
    r"(\d+[a-z]?(?:\s*\([\w.-]+\))?)"
)
_RECEIPT_ANCHOR = re.compile(r"(?i)\b(?:of|after|from)\s+(?:the\s+)?receipt\b")
_NEARBY_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9/-]{1,12}\b")
_IDENTIFIER_STOP_WORDS = {
    "section", "sec", "article", "art", "no", "of", "the", "and", "in", "under", "as",
}


def _safe_schema_message(exc: PydanticValidationError) -> str:
    """Summarize schema paths without returning rejected input values."""
    locations = [
        ".".join(str(part) for part in error.get("loc", ()))
        for error in exc.errors(include_input=False, include_url=False)
    ]
    path_summary = ", ".join(path for path in locations[:4] if path)
    if path_summary:
        return f"Payload does not match the required schema at: {path_summary}."
    return "Payload does not match the required schema."


def _parse_payload(model: type[_Model], payload: _Model | Mapping[str, Any]) -> tuple[_Model | None, ValidationIssue | None]:
    try:
        raw_payload = payload.model_dump(mode="python") if isinstance(payload, model) else payload
        return model.model_validate(raw_payload), None
    except PydanticValidationError as exc:
        return None, ValidationIssue(
            code="schema_invalid",
            message=_safe_schema_message(exc),
        )


def _reference_map(
    references: Iterable[ReferenceRecord | CuratedReference],
) -> dict[str, CuratedReference]:
    result: dict[str, CuratedReference] = {}
    for value in references:
        entry = value if isinstance(value, CuratedReference) else CuratedReference(record=value)
        result.setdefault(entry.record.reference_id, entry)
    return result


def _ascii_digits(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(_DIGIT_TRANSLATION)


def _normalized_number(value: str) -> str:
    compact = value.replace(",", "").strip()
    try:
        number = Decimal(compact)
    except InvalidOperation:
        return compact
    normalized = format(number.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _date_signatures(text: str) -> set[str]:
    text = _ascii_digits(text)
    mentions: set[str] = set()
    for match in _NUMERIC_DATE.finditer(text):
        first, _, second, _, third = match.groups()
        first_number, second_number, third_number = (int(part) for part in (first, second, third))
        if first_number >= 1000:
            mentions.add(f"date:{first_number}/{second_number}/{third_number}")
        elif third_number >= 1000:
            if first_number > 12:
                mentions.add(f"date:{third_number}/{second_number}/{first_number}")
            elif second_number > 12:
                mentions.add(f"date:{third_number}/{first_number}/{second_number}")
            else:
                # When day/month order is genuinely ambiguous, preserve both
                # interpretations rather than guessing the user's locale.
                mentions.add(f"date:{third_number}/{second_number}/{first_number}")
                mentions.add(f"date:{third_number}/{first_number}/{second_number}")
        else:
            mentions.add(f"date:{first_number}/{second_number}/{third_number}")
    for match in _ISO_DATE.finditer(text):
        year, month, day = match.groups()
        mentions.add(f"date:{int(year)}/{int(month)}/{int(day)}")
    for pattern, month_first in ((_MONTH_FIRST_DATE, True), (_DAY_FIRST_DATE, False)):
        for match in pattern.finditer(text):
            first, second, third = match.groups()
            if month_first:
                month, day, year = _MONTHS[first.casefold()], second, third
            else:
                day, month, year = first, _MONTHS[second.casefold()], third
            mentions.add(f"date:{int(year)}/{int(month)}/{int(day)}")
    return mentions


def _currency_code(token: str) -> str:
    lowered = token.casefold().replace(".", "").strip()
    if token in {"₹"} or lowered in {"rs", "inr", "rupee", "rupees", "रुपये", "रुपया", "रुपयों", "ਰੁਪਏ", "ਰੁਪਿਆ"}:
        return "INR"
    if token in {"$"} or lowered in {"usd", "us$", "dollar", "dollars"}:
        return "USD"
    if token == "€" or lowered in {"eur", "euro", "euros"}:
        return "EUR"
    if token == "£" or lowered in {"gbp", "pound", "pounds"}:
        return "GBP"
    return lowered.upper()


def _critical_mentions(text: str) -> set[str]:
    """Extract literal amounts, rates, durations, dates, and section IDs."""
    normalized = _ascii_digits(text)
    mentions = _date_signatures(normalized)

    for match in _AMOUNT.finditer(normalized):
        if match.group("value") is not None:
            currency = match.group(0)[: match.start("value") - match.start()].strip()
            value = match.group("value")
        else:
            currency = match.group("currency_words")
            value = match.group("value_words")
        mentions.add(f"amount:{_currency_code(currency)}:{_normalized_number(value)}")

    for value in _PERCENT.findall(normalized):
        mentions.add(f"percent:{_normalized_number(value)}")
    for value, unit in _DURATION.findall(normalized):
        canonical_unit = _DURATION_UNIT.get(unit.casefold())
        if canonical_unit is not None:
            mentions.add(f"duration:{_normalized_number(value)}:{canonical_unit}")
    for match in _SECTION.finditer(normalized):
        kind, identifier = match.groups()
        section_kind = "article" if kind.casefold().startswith("art") or kind in {"अनुच्छेद","ਅਨੁਛੇਦ"} else "section"
        compact = re.sub(r"\s+", "", identifier).casefold()
        mentions.add(f"{section_kind}:{compact}")
        context_start = max(0, match.start() - 28)
        context_end = min(len(normalized), match.end() + 28)
        context = normalized[context_start:context_end]
        candidates = []
        for token in _NEARBY_IDENTIFIER.finditer(context):
            word = token.group(0)
            if word.casefold() in _IDENTIFIER_STOP_WORDS:
                continue
            if not (word.isupper() or any(char.isupper() for char in word[1:])):
                continue
            candidates.append((abs((context_start + token.start()) - match.start()), word.casefold()))
        if candidates:
            _, law_identifier = min(candidates)
            mentions.add(f"{section_kind}_law:{law_identifier}:{compact}")
    return mentions


def _known_reference_context(
    reference_ids: Iterable[str], trusted: Mapping[str, CuratedReference]
) -> list[str]:
    context: list[str] = []
    for reference_id in reference_ids:
        entry = trusted.get(reference_id)
        if entry is not None:
            record = entry.record
            context.extend(
                part
                for part in (entry.law, record.title, record.section, record.version, record.excerpt)
                if part
            )
    return context


def _check_reference_ids(
    reference_ids: Iterable[str],
    trusted: Mapping[str, CuratedReference],
    *,
    item_id: str | None = None,
) -> list[ValidationIssue]:
    issues = []
    for reference_id in reference_ids:
        if reference_id not in trusted:
            issues.append(
                ValidationIssue(
                    code="unknown_reference_id",
                    message="A cited reference ID is not in the curated trusted-reference set.",
                    item_id=item_id,
                )
            )
    return issues


def _validate_evidence(
    evidence: Iterable[Any],
    clauses: Mapping[str, str],
    *,
    item_id: str | None = None,
) -> tuple[list[ValidationIssue], list[str]]:
    issues: list[ValidationIssue] = []
    quotes: list[str] = []
    for citation in evidence:
        original = clauses.get(citation.clause_id)
        if original is None:
            issues.append(
                ValidationIssue(
                    code="unknown_clause_id",
                    message="Evidence cites a clause outside the current reviewed request.",
                    clause_id=citation.clause_id,
                    item_id=item_id,
                )
            )
            continue
        if citation.quote not in original:
            issues.append(
                ValidationIssue(
                    code="quote_not_in_reviewed_text",
                    message="Evidence quote is not an exact substring of that clause's reviewed text.",
                    clause_id=citation.clause_id,
                    item_id=item_id,
                )
            )
            continue
        quotes.append(citation.quote)
    return issues, quotes


def _check_critical_literals(
    output_text: str,
    evidence_quotes: Iterable[str],
    reference_context: Iterable[str],
    *,
    item_id: str | None = None,
    clause_id: str | None = None,
) -> list[ValidationIssue]:
    generated = _critical_mentions(output_text)
    if not generated:
        return []
    supported: set[str] = set()
    for source in (*tuple(evidence_quotes), *tuple(reference_context)):
        supported.update(_critical_mentions(source))
    if generated.issubset(supported):
        return []
    return [
        ValidationIssue(
            code="unsupported_critical_literal",
            message="Output contains a date, amount, duration, rate, or section ID absent from cited evidence and trusted references.",
            clause_id=clause_id,
            item_id=item_id,
        )
    ]


_ALLEGATION_MARKERS = re.compile(
    r"(?i)\b(?:allege(?:s|d)?|allegedly|accused|according\s+to\s+(?:the\s+)?(?:complaint|fir)|"
    r"report(?:s|ed)?|(?:the\s+)?(?:fir|complaint)\s+(?:states|records|alleges|reports))\b|"
    r"आरोप|कथित|शिकायत|आरोपित|ਇਲਜ਼ਾਮ|ਦੋਸ਼|ਕਥਿਤ|ਸ਼ਿਕਾਇਤ|ਮੁਲਜ਼ਮ"
)
_RECEIPT_DATE_IN_TEXT = re.compile(
    r"(?i)(?:receipt|received|रसीद|प्राप्त|ਪ੍ਰਾਪਤੀ|ਮਿਲਣ)\D{0,24}"
    r"(?:\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|\d{4}-\d{1,2}-\d{1,2})"
)


def _validate_deadline(
    deadline: Any,
    clauses: Mapping[str, str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    reviewed_text = clauses.get(deadline.clause_id)
    if reviewed_text is None:
        return [
            ValidationIssue(
                code="unknown_clause_id",
                message="Deadline cites a clause outside the current reviewed request.",
                clause_id=deadline.clause_id,
                item_id=deadline.deadline_id,
            )
        ]
    if deadline.source_quote not in reviewed_text:
        issues.append(
            ValidationIssue(
                code="deadline_quote_not_in_reviewed_text",
                message="Deadline source quote is not an exact substring of reviewed text.",
                clause_id=deadline.clause_id,
                item_id=deadline.deadline_id,
            )
        )

    if _RECEIPT_ANCHOR.search(deadline.source_quote):
        has_receipt_date = bool(_RECEIPT_DATE_IN_TEXT.search(reviewed_text))
        if not has_receipt_date:
            if deadline.resolved_date is not None:
                issues.append(
                    ValidationIssue(
                        code="receipt_deadline_resolved_without_anchor",
                        message="A receipt-relative period cannot have a resolved date without a receipt date.",
                        clause_id=deadline.clause_id,
                        item_id=deadline.deadline_id,
                    )
                )
            if "receipt_date" not in deadline.missing_information:
                issues.append(
                    ValidationIssue(
                        code="receipt_date_not_marked_missing",
                        message="A receipt-relative period without a receipt date must name receipt_date as missing information.",
                        clause_id=deadline.clause_id,
                        item_id=deadline.deadline_id,
                    )
                )
            if deadline.status != "needs_information":
                issues.append(
                    ValidationIssue(
                        code="receipt_deadline_status_invalid",
                        message="A receipt-relative period without an anchor must use needs_information status.",
                        clause_id=deadline.clause_id,
                        item_id=deadline.deadline_id,
                    )
                )
    if deadline.resolved_date is not None:
        resolved = deadline.resolved_date.isoformat()
        if not any(signature == f"date:{deadline.resolved_date.year}/{deadline.resolved_date.month}/{deadline.resolved_date.day}" for signature in _date_signatures(reviewed_text)):
            issues.append(
                ValidationIssue(
                    code="derived_deadline_date_not_supported",
                    message="A resolved date must appear explicitly in the reviewed clause; v1 does not calculate legal deadlines.",
                    clause_id=deadline.clause_id,
                    item_id=deadline.deadline_id,
                )
            )
    return issues


def validate_analysis_result(
    result: AnalysisResult | Mapping[str, Any],
    request: AnalysisRequest,
    trusted_references: Iterable[ReferenceRecord | CuratedReference] = (),
) -> ValidationReport:
    """Validate a result against one current request and curated references.

    This checks structure and literal evidence relationships, not semantic
    entailment or the legal correctness of an explanation.
    """
    parsed, schema_issue = _parse_payload(AnalysisResult, result)
    if schema_issue is not None or parsed is None:
        return ValidationReport(valid=False, issues=[schema_issue] if schema_issue else [])
    result_model = parsed
    trusted = _reference_map(trusted_references)
    clauses = {clause.clause_id: clause.reviewed_text for clause in request.clauses}
    issues: list[ValidationIssue] = []

    for field in ("document_id", "analysis_id", "document_revision", "document_type", "input_language", "output_language"):
        if getattr(result_model, field) != getattr(request, field):
            issues.append(
                ValidationIssue(
                    code=f"{field}_mismatch",
                    message=f"Result {field} does not match the current analysis request.",
                )
            )
    if result_model.coverage.total != len(request.clauses):
        issues.append(
            ValidationIssue(
                code="coverage_total_mismatch",
                message="Coverage total must equal the number of clauses in the current request.",
            )
        )

    result_reference_ids: set[str] = set()
    for record in result_model.references:
        if record.reference_id in result_reference_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate_reference_record",
                    message="Result contains a duplicate reference record ID.",
                )
            )
        result_reference_ids.add(record.reference_id)
        trusted_entry = trusted.get(record.reference_id)
        if trusted_entry is None:
            issues.append(
                ValidationIssue(
                    code="unknown_reference_record",
                    message="Result contains a reference record outside the curated trusted-reference set.",
                )
            )
        elif record != trusted_entry.record:
            issues.append(
                ValidationIssue(
                    code="reference_record_mismatch",
                    message="Result reference metadata does not match the curated trusted record.",
                )
            )

    for item in result_model.items:
        if item.clause_id not in clauses:
            issues.append(
                ValidationIssue(
                    code="unknown_clause_id",
                    message="Result item cites a clause outside the current reviewed request.",
                    clause_id=item.clause_id,
                    item_id=item.item_id,
                )
            )
        evidence_issues, evidence_quotes = _validate_evidence(
            item.evidence, clauses, item_id=item.item_id
        )
        issues.extend(evidence_issues)
        if item.review_status == "supported" and not item.evidence:
            issues.append(
                ValidationIssue(
                    code="supported_item_without_evidence",
                    message="A supported result item must include source evidence.",
                    clause_id=item.clause_id,
                    item_id=item.item_id,
                )
            )
        issues.extend(
            _check_reference_ids(item.reference_ids, trusted, item_id=item.item_id)
        )
        reference_context = _known_reference_context(item.reference_ids, trusted)
        issues.extend(
            _check_critical_literals(
                item.explanation,
                evidence_quotes,
                reference_context,
                item_id=item.item_id,
                clause_id=item.clause_id,
            )
        )
        if request.document_type == "fir" and item.detector == "classifier":
            issues.append(
                ValidationIssue(
                    code="fir_classifier_bypass_violation",
                    message="The agreement classifier must not be applied to FIR content.",
                    clause_id=item.clause_id,
                    item_id=item.item_id,
                )
            )
        if (
            request.document_type == "fir"
            and item.kind == "allegation"
            and not _ALLEGATION_MARKERS.search(item.explanation)
        ):
            issues.append(
                ValidationIssue(
                    code="fir_allegation_framing_missing",
                    message="FIR allegation explanations must retain allegation or report wording.",
                    clause_id=item.clause_id,
                    item_id=item.item_id,
                )
            )

    for deadline in result_model.deadlines:
        issues.extend(_validate_deadline(deadline, clauses))
        if deadline.clause_id in clauses and deadline.source_quote in clauses[deadline.clause_id]:
            issues.extend(
                _check_critical_literals(
                    deadline.display_text,
                    [deadline.source_quote],
                    (),
                    item_id=deadline.deadline_id,
                    clause_id=deadline.clause_id,
                )
            )

    return ValidationReport(valid=not issues, issues=issues)


def validate_question_answer(
    answer: QuestionAnswer | Mapping[str, Any],
    question_request: QuestionRequest,
    analysis_request: AnalysisRequest,
    trusted_references: Iterable[ReferenceRecord | CuratedReference] = (),
) -> ValidationReport:
    """Bind a question response to the current analysis and validate its cites."""
    parsed, schema_issue = _parse_payload(QuestionAnswer, answer)
    if schema_issue is not None or parsed is None:
        return ValidationReport(valid=False, issues=[schema_issue] if schema_issue else [])
    answer_model = parsed
    issues: list[ValidationIssue] = []

    bindings = (
        ("document_id", question_request.document_id, analysis_request.document_id),
        ("analysis_id", question_request.analysis_id, analysis_request.analysis_id),
        ("document_revision", question_request.document_revision, analysis_request.document_revision),
        ("output_language", question_request.output_language, analysis_request.output_language),
    )
    for name, question_value, analysis_value in bindings:
        if question_value != analysis_value:
            issues.append(
                ValidationIssue(
                    code=f"question_{name}_mismatch",
                    message=f"Question request {name} does not match the current analysis request.",
                )
            )

    trusted = _reference_map(trusted_references)
    clauses = {clause.clause_id: clause.reviewed_text for clause in analysis_request.clauses}
    evidence_issues, evidence_quotes = _validate_evidence(answer_model.evidence, clauses)
    issues.extend(evidence_issues)
    if answer_model.review_status == "supported" and not answer_model.evidence:
        issues.append(
            ValidationIssue(
                code="supported_answer_without_evidence",
                message="A supported answer must include source evidence.",
            )
        )
    issues.extend(_check_reference_ids(answer_model.reference_ids, trusted))
    reference_context = _known_reference_context(answer_model.reference_ids, trusted)
    issues.extend(
        _check_critical_literals(
            answer_model.answer,
            evidence_quotes,
            reference_context,
        )
    )
    return ValidationReport(valid=not issues, issues=issues)
