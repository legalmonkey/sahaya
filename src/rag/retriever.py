"""Retrievers (spec: §7 / §21). One interface, two strategies, one chunk store:

- EmbeddingRetriever  — semantic, MiniLM embeddings + Chroma cosine search (Day 1 default)
- TfidfRetriever      — lexical baseline over the SAME store (no embedding model needed)

Selection: RETRIEVER=embedding | tfidf  in .env. Not two RAG pipelines — one pipeline,
one store, interchangeable retrievers.
"""
from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

from ..config import SETTINGS
from ..ingestion.embedder import get_embedding_provider
from .store import VectorStore


@dataclass
class RetrievedChunk:
    text: str
    document: str
    page: int
    section: str | None
    similarity: float
    chunk_id: str

    def source_dict(self) -> dict:
        return {
            "document": self.document,
            "page": self.page,
            "section": self.section,
            "similarity": round(self.similarity, 4),
            "chunk_id": self.chunk_id,
            "content": self.text,
            "text": self.text,
        }


class Retriever(ABC):
    name: str = "base"

    @abstractmethod
    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        ...


class EmbeddingRetriever(Retriever):
    name = "embedding"

    def __init__(self, embedder, store: VectorStore, k: int, threshold: float) -> None:
        self.embedder = embedder
        self.store = store
        self.k = k
        self.threshold = threshold

    @property
    def corpus_size(self) -> int:
        return self.store.count

    def documents(self) -> list[str]:
        return self.store.documents()

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        k = k or self.k
        if self.store.count == 0:
            return []
        # oversample, then drop below-threshold chunks, then cut to k —
        # irrelevant results are NOT returned just because they rank top-k (spec §7)
        n = min(max(k * 3, k + 5), self.store.count)
        emb = self.embedder.embed_query(query)
        hits = self.store.query(emb, n)
        kept = [h for h in hits if h["similarity"] >= self.threshold][:k]
        return [RetrievedChunk(
            text=h["text"], document=h["document"], page=h["page"],
            section=h["section"], similarity=h["similarity"], chunk_id=h["chunk_id"],
        ) for h in kept]


_STOP = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the to was "
    "were will with what when where which who whom this these those not no do does did "
    "can could should would may might must shall your you their our if then than so such"
    .split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


class TfidfRetriever(Retriever):
    """Pure-python TF-IDF over the same persisted chunks. Lexical similarity is on a
    DIFFERENT scale than embedding cosine — use TFIDF_THRESHOLD, not the cosine one."""

    name = "tfidf"

    def __init__(self, store: VectorStore, k: int, threshold: float = 0.02) -> None:
        self.store = store
        self.k = k
        self.threshold = threshold
        self._index = None   # list[(vec, norm, chunkinfo)] — built lazily (<1s for ~1k chunks)

    @property
    def corpus_size(self) -> int:
        return self.store.count

    def documents(self) -> list[str]:
        return self.store.documents()

    def _build(self) -> None:
        docs = []
        for c in self.store.iter_chunks():
            toks = _tok(c["text"])
            if toks:
                docs.append((toks, c))
        n_docs = max(1, len(docs))
        df: dict[str, int] = {}
        for toks, _ in docs:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        idf = {t: math.log((n_docs + 1) / (d + 1)) + 1.0 for t, d in df.items()}
        index = []
        for toks, c in docs:
            tf = Counter(toks)
            vec = {t: (n / len(toks)) * idf[t] for t, n in tf.items()}
            norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
            index.append((vec, norm, c))
        self._index = index

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        k = k or self.k
        if self._index is None:
            self._build()
        if not self._index:
            return []
        qtoks = _tok(query)
        if not qtoks:
            return []
        qtf = Counter(qtoks)
        qvec = {t: qtf[t] / len(qtoks) for t in qtf}
        qnorm = math.sqrt(sum(w * w for w in qvec.values())) or 1.0
        scored = []
        for vec, norm, c in self._index:
            dot = sum(w * vec[t] for t, w in qvec.items() if t in vec)
            if dot > 0:
                scored.append((dot / (qnorm * norm), c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [RetrievedChunk(
            text=c["text"], document=c["document"], page=c["page"],
            section=c["section"], similarity=round(sim, 4), chunk_id=c["chunk_id"],
        ) for sim, c in scored[:k] if sim >= self.threshold]


# ---------------------------------------------------------------------------
# Generic chunk reranking
# ---------------------------------------------------------------------------

def _extract_age_phrases(text: str) -> list[str]:
    """Extract age/time phrases for exact matching (generic regex, not query-specific)."""
    phrases: list[str] = []
    for m in re.finditer(
        r'\b(?:at\s+)?(?:\d+(?:-\d+)?\s+(?:week|month|year)s?|birth)\b', text
    ):
        phrases.append(m.group())
    return phrases


def rerank_chunks(
    query: str, chunks: list[RetrievedChunk], max_chunks: int = 2
) -> list[RetrievedChunk]:
    """Rerank retrieved chunks by combined semantic + lexical relevance with diversity.

    Uses generic signals (lexical overlap, phrase matching, source quality, diversity)
    instead of query-specific hardcoded rules.
    """
    if not chunks:
        return []
    if len(chunks) <= max_chunks:
        return list(chunks)

    q_tokens = set(_tok(query))
    q_lower = query.lower()
    age_phrases = _extract_age_phrases(q_lower)

    scored: list[tuple[float, RetrievedChunk]] = []
    for c in chunks:
        score = c.similarity  # base: semantic similarity

        c_tokens = set(_tok(c.text))
        c_lower = c.text.lower()

        # Lexical overlap: fraction of query content words found in chunk
        if q_tokens:
            overlap = len(q_tokens & c_tokens) / len(q_tokens)
            score += 0.15 * overlap

        # Exact age/time phrase match
        for phrase in age_phrases:
            if phrase in c_lower:
                score += 0.1

        # Source quality: structured/official documents get mild generic boost
        doc_lower = c.document.lower()
        if any(kw in doc_lower for kw in ("schedule", "handbook", "guideline")):
            score += 0.05

        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Select with diversity: skip near-duplicate chunks (Jaccard > 0.7)
    selected: list[RetrievedChunk] = []
    seen_token_sets: list[set[str]] = []
    for _, c in scored:
        c_tok_set = set(_tok(c.text))
        is_dup = False
        for seen in seen_token_sets:
            if c_tok_set and seen:
                union = len(c_tok_set | seen)
                if union > 0 and len(c_tok_set & seen) / union > 0.7:
                    is_dup = True
                    break
        if not is_dup:
            selected.append(c)
            seen_token_sets.append(c_tok_set)
        if len(selected) >= max_chunks:
            break

    return selected


def get_retriever() -> Retriever:
    store = VectorStore(SETTINGS.vector_db_dir, SETTINGS.collection_name)
    if SETTINGS.retriever == "embedding":
        return EmbeddingRetriever(
            get_embedding_provider(), store, SETTINGS.top_k, SETTINGS.similarity_threshold
        )
    if SETTINGS.retriever == "tfidf":
        return TfidfRetriever(store, SETTINGS.top_k, SETTINGS.tfidf_threshold)
    raise ValueError(f"Unknown RETRIEVER '{SETTINGS.retriever}' (use 'embedding' or 'tfidf')")