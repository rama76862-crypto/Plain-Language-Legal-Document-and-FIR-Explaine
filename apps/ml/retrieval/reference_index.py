"""Lookup over a caller-supplied curated reference collection.

This module contains no legal reference data. Entries must be curated elsewhere;
semantic BM25 matches are candidates and are not proof that a source applies.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from apps.ml.service.contracts import ReferenceRecord, RetrievalHit

from ._bm25 import BM25Index, tokenize


@dataclass(frozen=True, slots=True)
class CuratedReference:
    """Internal index metadata missing from the public v1 reference shape."""

    record: ReferenceRecord
    law: str | None = None


@dataclass(frozen=True, slots=True)
class OfficialReferenceMatch:
    """A curated source candidate and whether its section matched exactly."""

    hit: RetrievalHit
    exact_section_match: bool


def _normalize_metadata(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return normalized or None


def _reference_text(entry: CuratedReference) -> str:
    record = entry.record
    return " ".join(
        part for part in (entry.law, record.title, record.section, record.excerpt) if part
    )


def find_official_references(
    entries: Iterable[CuratedReference],
    query: str,
    *,
    section: str | None = None,
    law: str | None = None,
    jurisdiction: str | None = None,
    version: str | None = None,
    limit: int = 5,
) -> list[OfficialReferenceMatch]:
    """Filter curated records, then prefer exact sections before lexical fallback.

    When an exact section is supplied and found, only exact hits are returned.
    If it is not found, BM25 can return filtered candidate references for review;
    callers must not present a semantic candidate as an exact legal match.
    """
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit == 0:
        return []

    normalized_law = _normalize_metadata(law)
    normalized_jurisdiction = _normalize_metadata(jurisdiction)
    normalized_version = _normalize_metadata(version)
    normalized_section = _normalize_metadata(section)

    filtered = [
        entry
        for entry in entries
        if (normalized_law is None or _normalize_metadata(entry.law) == normalized_law)
        and (
            normalized_jurisdiction is None
            or _normalize_metadata(entry.record.jurisdiction) == normalized_jurisdiction
        )
        and (
            normalized_version is None
            or _normalize_metadata(entry.record.version) == normalized_version
        )
    ]
    if not filtered:
        return []

    if normalized_section is not None:
        exact = [
            entry
            for entry in filtered
            if _normalize_metadata(entry.record.section) == normalized_section
        ]
        if exact:
            return [
                OfficialReferenceMatch(
                    hit=RetrievalHit(
                        record_id=entry.record.reference_id,
                        text=entry.record.excerpt,
                        # Exactness is exposed separately; do not make this look
                        # like a calibrated similarity score.
                        score=0.0,
                        source_kind="official_reference",
                        reference=entry.record,
                    ),
                    exact_section_match=True,
                )
                for entry in exact[:limit]
            ]

    query_tokens = tokenize(query)
    bm25 = BM25Index([tokenize(_reference_text(entry)) for entry in filtered])
    scores = bm25.score(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda pair: (-pair[1], pair[0]))
    matches: list[OfficialReferenceMatch] = []
    for index, score in ranked:
        if score <= 0.0:
            continue
        entry = filtered[index]
        matches.append(
            OfficialReferenceMatch(
                hit=RetrievalHit(
                    record_id=entry.record.reference_id,
                    text=entry.record.excerpt,
                    score=score,
                    source_kind="official_reference",
                    reference=entry.record,
                ),
                exact_section_match=False,
            )
        )
        if len(matches) >= limit:
            break
    bm25.clear()
    return matches
