"""Small reviewed attention cues for agreements; these are not legal judgments."""

from __future__ import annotations

import re

from apps.ml.service.contracts import AnalysisItem, ClauseInput, DocumentType, Evidence

_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "automatic_renewal",
        re.compile(
            r"\b(?:automatic(?:ally)?\s*[- ]?\s*renew(?:s|ed|ing|al)?|"
            r"auto[- ]?renew(?:al|s|ed|ing)?|renew(?:s|ed|ing)?\s+automatically)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "payment_penalty",
        re.compile(
            r"\b(?:late\s+(?:payment\s+)?(?:fees?|charges?|penalt(?:y|ies))|"
            r"(?:pre[- ]?payment|payment|repayment)\s+penalt(?:y|ies)|"
            r"penalt(?:y|ies)\s+(?:for|on)\s+(?:(?:late|missed|overdue)\s+payment|non[- ]?payment))\b",
            re.IGNORECASE,
        ),
    ),
)

_SCOPE_BREAK = re.compile(r"[.;!?\n]")
_NEGATION_AT_END = re.compile(
    r"\b(?:no|not|never|without|exclude(?:s|d)?|does\s+not|do\s+not|did\s+not|will\s+not|"
    r"shall\s+not|would\s+not|should\s+not|is\s+not|are\s+not|was\s+not|"
    r"were\s+not|has\s+not|have\s+not|had\s+not)\b(?:\s+[\w'-]+){0,3}\s*$",
    re.IGNORECASE,
)
_NEGATED_PREDICATE = re.compile(
    r"^\s*(?:(?:[\w'-]+\s+){0,2})?(?:(?:does|do|did|will|shall|would|should|is|are|was|were|has|have|had)"
    r"\s+not\s+(?:be\s+)?|(?:is|are|was|were|will\s+be|shall\s+be)\s+)"
    r"(?:applicable|apply|charged|imposed|levied|required|permitted|allowed|"
    r"available|effective|enforceable|included|part\s+of|excluded|exempt|"
    r"excepted|prohibited)\b",
    re.IGNORECASE,
)


def _scope_before(text: str, position: int) -> str:
    prefix = text[:position]
    boundary = max((match.end() for match in _SCOPE_BREAK.finditer(prefix)), default=0)
    return prefix[boundary:]


def _scope_after(text: str, position: int) -> str:
    suffix = text[position:]
    boundary = _SCOPE_BREAK.search(suffix)
    return suffix[: boundary.start()] if boundary else suffix


def _is_explicitly_negated(text: str, match: re.Match[str]) -> bool:
    before = _scope_before(text, match.start())
    after = _scope_after(text, match.end())
    return bool(_NEGATION_AT_END.search(before) or _NEGATED_PREDICATE.match(after))


def agreement_attention_items(
    clause: ClauseInput,
    *,
    document_type: DocumentType = "agreement",
) -> list[AnalysisItem]:
    """Return cue-only attention items for an agreement clause.

    A direct negation or explicit carve-out suppresses the cue. A positive
    default that is limited by an opt-out/cure period remains an attention cue.
    The caller must use this only as a reviewed lexical rule, not as a finding
    that a term is unlawful or unenforceable.
    """
    if document_type != "agreement":
        return []

    items: list[AnalysisItem] = []
    for category, pattern in _CUES:
        match = next(
            (
                candidate
                for candidate in pattern.finditer(clause.reviewed_text)
                if not _is_explicitly_negated(clause.reviewed_text, candidate)
            ),
            None,
        )
        if match is None:
            continue
        if category == "automatic_renewal":
            explanation = (
                "This wording describes automatic renewal; review the renewal term "
                "and any cancellation steps."
            )
        else:
            explanation = (
                "This wording describes a payment penalty or charge; review its amount "
                "and when it applies."
            )
        items.append(
            AnalysisItem(
                item_id=f"rule:{clause.clause_id}:{category}",
                clause_id=clause.clause_id,
                kind="attention",
                category=category,
                explanation=explanation,
                evidence=[Evidence(clause_id=clause.clause_id, quote=match.group(0))],
                review_status="supported",
                detector="rule",
                model_score=None,
                limitations=["lexical_cue_only_not_a_legal_assessment"],
            )
        )
    return items
