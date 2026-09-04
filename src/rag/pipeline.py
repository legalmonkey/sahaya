"""The RAG pipeline and the single public interface (spec: §11).

UIs (CLI today, Android later) call answer_query() only — they never touch the vector
store or the LLM provider directly.

Confidence: a weighted mean of retrieval similarities (top result weighted highest).
IMPORTANT — this is RETRIEVAL CONFIDENCE: how well the corpus matched the question.
It is NOT a measure of medical correctness or answer accuracy.
"""
from __future__ import annotations

import time

from ..config import SETTINGS
from ..llm.base import LLMError, create_llm_provider
from .conversation import ConversationBuffer, contextualize_query
from .prompt import INSUFFICIENT_INFO_ANSWER, SYSTEM_PROMPT, build_prompt
from .retriever import RetrievedChunk, Retriever, get_retriever

# Structured guardrail: when nothing relevant is retrieved we return this status
# INSTEAD of asking the LLM. This is a generic retrieval-safety behavior.
INSUFFICIENT_CONTEXT_MSG = INSUFFICIENT_INFO_ANSWER


def retrieval_confidence(similarities: list[float]) -> float:
    """Weighted mean of retrieval similarities, weights 1, 1/2, 1/3, ... (top first)."""
    if not similarities:
        return 0.0
    sims = sorted(similarities, reverse=True)
    weights = [1.0 / (i + 1) for i in range(len(sims))]
    val = sum(s * w for s, w in zip(sims, weights)) / sum(weights)
    return round(min(max(val, 0.0), 1.0), 4)


class RAGPipeline:
    def __init__(self, retriever: Retriever, llm) -> None:
        self.retriever = retriever
        self.llm = llm

    def answer_query(
        self,
        query: str,
        history: ConversationBuffer | list | None = None,
        child_context: dict | None = None,
    ) -> dict:
        t0 = time.perf_counter()
        question = (query or "").strip()
        if not question:
            return {"status": "error", "error": "Empty query.",
                    "answer": "", "sources": [], "confidence": 0.0,
                    "latency_ms": {"retrieval": 0, "llm": 0, "total": 0}}

        # Contextualize retrieval query with multi-turn history if present
        retrieval_query = contextualize_query(question, history=history, child_context=child_context)
        chunks = self.retriever.retrieve(retrieval_query)
        if not chunks and retrieval_query != question:
            chunks = self.retriever.retrieve(question)

        retrieval_ms = int((time.perf_counter() - t0) * 1000)

        if not chunks:
            return {
                "status": "insufficient_context",
                "answer": INSUFFICIENT_CONTEXT_MSG,
                "sources": [],
                "confidence": 0.0,
                "latency_ms": {"retrieval": retrieval_ms, "llm": 0,
                               "total": retrieval_ms},
            }

        prompt = build_prompt(question, chunks, history=history)
        t1 = time.perf_counter()
        try:
            answer = self.llm.generate(prompt, system=SYSTEM_PROMPT).strip()
        except LLMError as e:
            # Surface the real error — never a fake answer (spec §23).
            return {
                "status": "error",
                "error": str(e),
                "answer": "",
                "sources": [c.source_dict() for c in chunks],
                "confidence": 0.0,
                "latency_ms": {"retrieval": retrieval_ms, "llm": 0,
                               "total": int((time.perf_counter() - t0) * 1000)},
            }
        llm_ms = int((time.perf_counter() - t1) * 1000)

        return {
            "status": "ok",
            "answer": answer,
            "sources": [c.source_dict() for c in chunks],
            "confidence": retrieval_confidence([c.similarity for c in chunks]),
            "latency_ms": {"retrieval": retrieval_ms, "llm": llm_ms,
                           "total": int((time.perf_counter() - t0) * 1000)},
        }


_DEFAULT: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = RAGPipeline(get_retriever(), create_llm_provider())
    return _DEFAULT


def answer_query(
    query: str,
    history: ConversationBuffer | list | None = None,
    child_context: dict | None = None,
) -> dict:
    """Single public RAG interface — the only entry point any UI is allowed to call."""
    return get_pipeline().answer_query(query, history=history, child_context=child_context)


def corpus_stats() -> dict:
    r = get_pipeline().retriever
    return {"chunks": r.corpus_size, "documents": r.documents()}