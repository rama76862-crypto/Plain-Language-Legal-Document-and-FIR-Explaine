"""Dependency-free BM25 primitives for small, temporary in-memory indexes."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

_TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Return Unicode-aware word tokens without retaining source text globally."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return _TOKEN_PATTERN.findall(normalized)


class BM25Index:
    """Minimal Okapi BM25 ranking over a fixed set of short documents."""

    def __init__(self, documents: Sequence[Sequence[str]], *, k1: float = 1.5, b: float = 0.75):
        self._documents = [list(document) for document in documents]
        self._k1 = k1
        self._b = b
        self._lengths = [len(document) for document in self._documents]
        self._average_length = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        self._frequencies = [Counter(document) for document in self._documents]
        document_frequency: Counter[str] = Counter()
        for frequencies in self._frequencies:
            document_frequency.update(frequencies.keys())
        count = len(self._documents)
        self._inverse_document_frequency = {
            token: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def score(self, query_tokens: Sequence[str]) -> list[float]:
        """Return BM25 scores aligned to the indexed documents."""
        if not query_tokens or not self._documents:
            return [0.0] * len(self._documents)

        scores: list[float] = []
        for frequencies, length in zip(self._frequencies, self._lengths, strict=True):
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                inverse_frequency = self._inverse_document_frequency.get(token, 0.0)
                denominator = frequency + self._k1 * (
                    1.0 - self._b + self._b * length / (self._average_length or 1.0)
                )
                score += inverse_frequency * frequency * (self._k1 + 1.0) / denominator
            scores.append(score)
        return scores

    def clear(self) -> None:
        """Discard tokenized content and statistics for temporary-document cleanup."""
        self._documents.clear()
        self._lengths.clear()
        self._frequencies.clear()
        self._inverse_document_frequency.clear()
        self._average_length = 0.0
