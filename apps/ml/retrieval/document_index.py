"""Temporary retrieval over human-reviewed clauses in one document revision."""

from __future__ import annotations

from collections.abc import Sequence

from apps.ml.service.contracts import ClauseInput, RetrievalHit

from ._bm25 import BM25Index, tokenize


class LocalDocumentIndex:
    """An in-memory BM25 index; callers should discard it when a session ends."""

    def __init__(self, clauses: Sequence[ClauseInput]):
        self._clauses = tuple(clauses)
        clause_ids = [clause.clause_id for clause in self._clauses]
        if len(clause_ids) != len(set(clause_ids)):
            raise ValueError("clause_id values must be unique within a document index")
        self._bm25 = BM25Index([tokenize(clause.reviewed_text) for clause in self._clauses])
        self._closed = False

    def search(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        """Rank matching reviewed clauses; this is for context and questions only."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if self._closed or limit == 0:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.score(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda pair: (-pair[1], pair[0]))
        hits: list[RetrievalHit] = []
        for index, score in ranked:
            if score <= 0.0:
                continue
            clause = self._clauses[index]
            hits.append(
                RetrievalHit(
                    record_id=clause.clause_id,
                    text=clause.reviewed_text,
                    score=score,
                    source_kind="document",
                )
            )
            if len(hits) >= limit:
                break
        return hits

    def close(self) -> None:
        """Clear clause text and BM25 state when the owning session is deleted."""
        self._clauses = ()
        self._bm25.clear()
        self._closed = True


def build_document_index(clauses: Sequence[ClauseInput]) -> LocalDocumentIndex:
    """Construct a revision-scoped index over reviewed text only."""
    return LocalDocumentIndex(clauses)
