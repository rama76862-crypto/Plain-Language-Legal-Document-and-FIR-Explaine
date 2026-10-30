"""Small reviewed attention cues for agreements; these are not legal judgments."""

from __future__ import annotations

import re

from apps.ml.service.contracts import AnalysisItem, ClauseInput, DocumentType, Evidence

_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unilateral_change",
        re.compile(r"\b(?:provider|landlord|lender|bank|company|seller|employer)\b.{0,35}\b(?:may|can|reserves?\s+the\s+right\s+to)\s+(?:change|amend|vary|alter|modify|revise|update)\b.{0,45}\b(?:terms|fees|charges|interest\s+rates?)\b",re.I),
    ),
    (
        "automatic_renewal",
        re.compile(
            r"\b(?:automatic(?:ally)?\s*[- ]?\s*renew(?:s|ed|ing|al)?|"
            r"auto[- ]?renew(?:al|s|ed|ing)?|renew(?:s|ed|ing)?\s+automatically)\b|"
            r"स्वतः\s*नवीनी|अपने\s*आप\s*नवीनी|ਆਪਣੇ\s*ਆਪ\s*ਨਵੀ|ਆਟੋ.{0,8}ਨਵੀ",
            re.IGNORECASE,
        ),
    ),
    (
        "payment_penalty",
        re.compile(
            r"\b(?:late\s+(?:payment\s+)?(?:fees?|charges?|penalt(?:y|ies))|"
            r"(?:pre[- ]?payment|payment|repayment)\s+penalt(?:y|ies)|"
            r"penalt(?:y|ies)\s+(?:for|on)\s+(?:(?:late|missed|overdue)\s+payment|non[- ]?payment)|penalt(?:y|ies)|surcharge)\b|"
            r"जुर्माना|विलंब\s*शुल्क|देरी.{0,12}शुल्क|ਜੁਰਮਾਨਾ|ਦੇਰੀ.{0,12}ਫੀਸ",
            re.IGNORECASE,
        ),
    ),
    (
        "waived_rights",
        re.compile(r"\b(?:waiv(?:e|es|ed|ing)|give\s+up|surrender|relinquish\w*|abandon\w*)\b.{0,65}\b(?:rights?|claims?|appeal|refund|notice|remed(?:y|ies)|entitlement|ability\s+to\s+dispute)\b|\b(?:rights?|claims?)\b.{0,45}\bwaiv(?:e|es|ed|ing)\b|अधिकार.{0,30}(?:त्याग|छोड़)|(?:त्याग|छोड़).{0,30}अधिकार|ਹੱਕ.{0,30}ਛੱਡ|ਅਧਿਕਾਰ.{0,30}ਤਿਆਗ", re.I),
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
    r"\s+not\s+(?:(?:be|been)\s+)?(?:applicable|apply|charged|imposed|levied|required|permitted|allowed|available|effective|enforceable|included|part\s+of)"
    r"|(?:is|are|was|were|will\s+be|shall\s+be)\s+(?:excluded|exempt|excepted|prohibited))\b",
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
    return bool(_NEGATION_AT_END.search(before) or _NEGATED_PREDICATE.match(after)
                or re.search(r"\b(?:cannot|shall\s+not|will\s+not|does\s+not|not\s+be)\b|नहीं|ਨਹੀਂ", match.group(0), re.I)
                or re.match(r".{0,24}?(?:नहीं|ਨਹੀਂ)", after))


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
        if category == "unilateral_change" and re.search(r"(?:only\s+if|subject\s+to|with|requires?)\s+(?:the\s+)?(?:mutual|both\s+parties'|both\s+parties\s+to\s+give|customer's?\s+written)\s+(?:consent|agreement|approval)",clause.reviewed_text,re.I):
            continue
        if category == "automatic_renewal":
            explanation = (
                "This wording describes automatic renewal; review the renewal term "
                "and any cancellation steps."
            )
        elif category == "unilateral_change":
            explanation = "This wording allows the named party to change terms or charges; check the stated notice, conditions and any approval requirement."
        elif category == "waived_rights":
            explanation = (
                "This wording refers to giving up a right or claim; review exactly "
                "which right, the exceptions, and whether clarification is needed."
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


def candidate_supported(category: str, text: str) -> bool:
    """A classifier score cannot turn an ordinary payment into a penalty."""
    for name, pattern in _CUES:
        if category == name:
            return any(not _is_explicitly_negated(text,m) for m in pattern.finditer(text))
    anchors = {
        "deposit_forfeiture": r"(?:deposit|security|advance|earnest).{0,90}(?:forfeit|los[et]|retain|non.refundable|not.{0,12}return)|(?:forfeit|retain).{0,50}(?:deposit|security)",
        "unilateral_change": r"(?:may|can|reserves?).{0,65}(?:change|amend|vary|alter|modify|revise)|(?:sole|unilateral|discretion).{0,50}(?:change|amend|vary|alter)",
        "unilateral_termination": r"(?:may|can|reserves?).{0,65}(?:terminate|end|cancel|discontinue|close)|unilateral.{0,30}termination",
        "limitation_of_liability": r"(?:liab\w*|responsib\w*|compensation|recovery).{0,70}(?:limit|cap|restrict|exclud|not|no|exceed)|(?:not|no|limit|cap|disclaim|exclud).{0,50}(?:liab\w*|responsib\w*|compensation)",
    }
    return category not in anchors or bool(re.search(anchors[category], text, re.I))
