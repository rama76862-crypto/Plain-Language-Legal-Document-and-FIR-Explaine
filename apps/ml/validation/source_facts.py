"""Source-only facts and conservative checks, not a legal entailment oracle."""
from __future__ import annotations

import re
from typing import Any
from apps.ml.service.contracts import ClauseInput
from apps.ml.validation.result_validator import _critical_mentions

VERSION = "source-facts-v3"
_CONDITION = re.compile(r"\b(?:unless|except|provided\s+that|subject\s+to|only\s+if|if|until)\b|जब तक|यदि|बशर्ते|ਜੇ|ਜਦੋਂ ਤੱਕ", re.I)
_NEGATIVE = re.compile(r"\b(?:no|not|never|cannot|without|prohibit\w*|exclud\w*)\b|नहीं|नही|बिना|ਨਹੀਂ|ਬਿਨਾਂ", re.I)
_ANCHORS = {
    "receipt": re.compile(r"\b(?:receipt|received|receiving)\b|प्राप्ति|प्राप्त|ਪ੍ਰਾਪਤੀ|ਮਿਲਣ", re.I),
    "delivery": re.compile(r"\bdeliver(?:y|ed)\b|डिलीवरी|ਡਿਲੀਵਰੀ", re.I),
    "service": re.compile(r"\bserv(?:ice|ed)\b|तामील|ਤਾਮੀਲ", re.I),
    "due_date": re.compile(r"\bdue\s+date\b|\b(?:rent|payment|repayment|instalment|installment)\b.{0,40}\b(?:late|overdue|on\s+time)\b|\b(?:pay|paid)\b.{0,20}\bon\s+time\b|नियत तिथि|ਨਿਯਤ ਮਿਤੀ", re.I),
    "signature": re.compile(r"\b(?:signing|signature|signed)\b|हस्ताक्षर|ਦਸਤਖਤ", re.I),
}
_ROLE = re.compile(r"\b(?:landlord|tenant|borrower|lender|buyer|seller|complainant|accused|recipient|sender|employer|employee|customer|provider)\b", re.I)
_XREF = re.compile(r"\b(?:clause|paragraph|annexure|schedule)\s+([A-Z]?\d+(?:\.\d+)*|[A-Z])\b|(?:खंड|ਧਾਰਾ)\s*(\d+(?:\.\d+)*)", re.I)
_OBLIGATION = re.compile(r"\b(?:shall|must|required\s+to|agrees?\s+to|may|will)\b|होगा|करना होगा|ਲਾਜ਼ਮੀ|ਹੋਵੇਗਾ", re.I)

def document_profile(text: str, document_type: str) -> str:
    if document_type in {"fir", "notice"}:
        return document_type
    for profile, pattern in (
        ("loan", r"\b(?:borrower|lender|loan|instalment|installment|collateral)\b|ऋण|ਕਰਜ਼"),
        ("land", r"\b(?:sale\s+deed|khasra|khewat|conveyance|property\s+sale|land\s+agreement|title\s+(?:deed|documents))\b|खसरा|ਵਿਕਰੀ"),
        ("rent", r"\b(?:landlord|tenant|tenancy|lease|rent)\b|किराया|ਕਿਰਾਇਆ"),
    ):
        if re.search(pattern, text, re.I):
            return profile
    return "agreement" if document_type == "agreement" else "other"

def source_facts(clause: ClauseInput) -> dict[str, Any]:
    text = clause.reviewed_text
    sentences = [part.strip() for part in re.split(r"(?<=[.;!?।])\s+|\n+", text) if part.strip()]
    return {
        "clause_id": clause.clause_id,
        "critical_literals": sorted(_critical_mentions(text)),
        "roles": sorted({m.group().lower() for m in _ROLE.finditer(text)}),
        "anchors": [name for name, pattern in _ANCHORS.items() if pattern.search(text)],
        "conditions": [s for s in sentences if _CONDITION.search(s)],
        "negations": [s for s in sentences if _NEGATIVE.search(s)],
        "obligations": [s for s in sentences if _OBLIGATION.search(s)],
        "cross_references": [m.group(1) or m.group(2) for m in _XREF.finditer(text)],
        "source_ref": clause.source_ref.model_dump(mode="json") if clause.source_ref else None,
        "method": VERSION,
        "semantic_review": "not_independently_reviewed",
    }

def grounding_issues(source: str, summary: str, *, output_language: str = "en", require_coverage: bool = True) -> list[str]:
    """Passing necessary literal checks is not proof of legal correctness."""
    original, generated = _critical_mentions(source), _critical_mentions(summary)
    issues = []
    if generated - original:
        issues.append("unsupported_critical_literal")
    if require_coverage and original - generated:
        issues.append("omitted_critical_literal")
    if output_language != "en" or re.search(r"[\u0900-\u097f\u0a00-\u0a7f]", source):
        return issues
    if require_coverage and _CONDITION.search(source) and not _CONDITION.search(summary):
        issues.append("omitted_condition_or_exception")
    if require_coverage and _NEGATIVE.search(source) and not _NEGATIVE.search(summary):
        issues.append("omitted_negation")
    for name, pattern in _ANCHORS.items():
        if pattern.search(summary) and not pattern.search(source):
            issues.append(f"unsupported_anchor:{name}")
        if require_coverage and name in {"receipt","delivery","service","signature"} and pattern.search(source) and not pattern.search(summary):
            issues.append(f"omitted_anchor:{name}")
    if re.search(r"\bconsent\b", summary, re.I) and not re.search(r"\b(?:consent|permission|authori[sz])\w*\b", source, re.I):
        issues.append("unsupported_consent_claim")
    if (require_coverage or re.search(r"\b(?:if|unless|within|after|before|when)\b",summary,re.I)) and re.search(r"payment.{0,25}receiv|receiv.{0,25}payment", source, re.I) and not re.search(r"payment.{0,25}receiv|receiv.{0,25}payment", summary, re.I):
        issues.append("payment_received_changed_to_payment_made")
    if re.search(r"receiving\s+a\s+receipt", summary, re.I) and not re.search(r"receiving\s+a\s+receipt", source, re.I):
        issues.append("receipt_event_invented")
    source_roles = {m.group().lower() for m in _ROLE.finditer(source)}
    generated_roles = {m.group().lower() for m in _ROLE.finditer(summary)}
    if source_roles and generated_roles - source_roles:
        issues.append("unsupported_actor")
    if re.search(r"\b(?:penalt\w*|late\s+fee)\b", summary, re.I) and not re.search(r"\b(?:penalt\w*|fee|charge)\b", source, re.I):
        issues.append("unsupported_penalty")
    return list(dict.fromkeys(issues))

def cross_reference_context(clause: ClauseInput, clauses: list[ClauseInput]) -> tuple[list[ClauseInput], list[str]]:
    by_id = {c.clause_id: c for c in clauses}
    for candidate in clauses:
        label = re.match(r"\s*(?:(?:clause|section|खंड|ਧਾਰਾ)\s+)?(\d+(?:\.\d+)*)[.)\s:]", candidate.reviewed_text, re.I)
        if label:
            by_id.setdefault(label.group(1), candidate)
    found, missing = [], []
    for match in _XREF.finditer(clause.reviewed_text):
        identifier = match.group(1) or match.group(2)
        target = by_id.get(identifier)
        if target and target.clause_id != clause.clause_id:
            if target not in found:
                found.append(target)
        elif target is None:
            missing.append(identifier)
    return found, list(dict.fromkeys(missing))

