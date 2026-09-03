"""Small local vector retrieval. No network dependency or remote embedding service."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


@dataclass(frozen=True)
class RetrievalResult:
    chunk: dict
    score: float


class LocalTfidfRetriever:
    """Fits a compact TF-IDF vector space over the bundled corpus on startup."""

    def __init__(self, corpus_path: Path):
        self.chunks = json.loads(corpus_path.read_text(encoding="utf-8"))
        if not self.chunks:
            raise ValueError("The local corpus cannot be empty.")
        documents = [tokenize(chunk["title"] + " " + chunk["text"]) for chunk in self.chunks]
        document_frequency = Counter(token for doc in documents for token in set(doc))
        total = len(documents)
        self.idf = {token: math.log((total + 1) / (frequency + 1)) + 1 for token, frequency in document_frequency.items()}
        self.vectors = [self._vectorize(tokens) for tokens in documents]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        weighted = {token: count * self.idf.get(token, 0.0) for token, count in counts.items() if token in self.idf}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        return {token: value / norm for token, value in weighted.items()} if norm else {}

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        return sum(value * right.get(token, 0.0) for token, value in left.items())

    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        if not query or not query.strip():
            raise ValueError("A question is required.")
        vector = self._vectorize(tokenize(query))
        scored = [RetrievalResult(chunk, self._cosine(vector, item)) for chunk, item in zip(self.chunks, self.vectors)]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    @staticmethod
    def confidence(results: list[RetrievalResult]) -> float:
        """A bounded, derived signal: top similarity weighted by separation from runner-up."""
        if not results or results[0].score <= 0:
            return 0.0
        second = results[1].score if len(results) > 1 else 0.0
        return round(min(1.0, results[0].score * 0.75 + max(0.0, results[0].score - second) * 0.25), 3)
