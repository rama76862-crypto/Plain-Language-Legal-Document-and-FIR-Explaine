"""Small in-memory retrieval helpers for reviewed clauses and curated sources."""

from .document_index import LocalDocumentIndex
from .reference_index import (
    CuratedReference,
    OfficialReferenceMatch,
    find_official_references,
)

__all__ = [
    "CuratedReference",
    "LocalDocumentIndex",
    "OfficialReferenceMatch",
    "find_official_references",
]
