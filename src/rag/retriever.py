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


def get_retriever() -> Retriever:
    store = VectorStore(SETTINGS.vector_db_dir, SETTINGS.collection_name)
    if SETTINGS.retriever == "embedding":
        return EmbeddingRetriever(
            get_embedding_provider(), store, SETTINGS.top_k, SETTINGS.similarity_threshold
        )
    if SETTINGS.retriever == "tfidf":
        return TfidfRetriever(store, SETTINGS.top_k, SETTINGS.tfidf_threshold)
    raise ValueError(f"Unknown RETRIEVER '{SETTINGS.retriever}' (use 'embedding' or 'tfidf')")