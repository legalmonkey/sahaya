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
from .retriever import RetrievedChunk, Retriever, get_retriever, rerank_chunks

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


GENERIC_QUERY_TERMS = frozenset({
    "what", "which", "when", "where", "who", "whom", "whose", "why", "how",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "should", "would", "will", "shall", "may", "might", "must",
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "for", "to", "in",
    "on", "at", "by", "with", "from", "about", "into", "through", "during", "before",
    "after", "above", "below", "between", "under", "this", "that", "these", "those",
    "it", "its", "they", "them", "their",
    "exact", "given", "give", "gives", "giving",
    "many", "much", "more", "most", "any", "some", "all",
    "child", "children", "infant", "infants", "baby", "babies",
    "patient", "person", "individual", "mother", "mothers",
    "dosage", "dose", "doses", "amount", "quantity", "level",
    "temperature", "concentration", "percentage", "rate",
})


def _has_sufficient_evidence(question: str, chunks) -> bool:
    """Generic evidence sufficiency check.

    Detects if the question requests a specific numeric/medical value (temperature,
    dosage, etc.) and verifies the retrieved sources contain explicit supporting
    evidence. Prevents the LLM from hallucinating medical numbers.

    Non-quantitative questions (schedule lookups, protocol questions) pass through.
    """
    if not chunks:
        return False

    import re
    from .retriever import _tok

    q_lower = question.lower()
    combined_lower = " ".join(c.text.lower() for c in chunks)

    # 1. Identify specific medical subject / entity terms in the question
    specific_terms = [t for t in _tok(question) if t not in GENERIC_QUERY_TERMS and len(t) >= 3]

    # Detect if question asks for numeric value or dosage amount
    asks_dosage = (
        bool(re.search(r'\bdosage\b', q_lower)) or
        bool(re.search(r'\b(?:dosage|dose)\s+of\b', q_lower)) or
        bool(re.search(r'what\s+is\s+the\s+(?:dosage|dose)\b', q_lower)) or
        bool(re.search(r'how\s+(?:much|many)\s+(?:mg|ml|mcg|drops?)\b', q_lower))
    )
    asks_numeric = any(k in q_lower for k in ("temperature", "concentration", "percentage", "rate")) or asks_dosage

    if asks_numeric:
        # If asking about a specific drug/substance dosage, that subject MUST appear in sources
        if specific_terms:
            subject_found = any(re.search(rf'\b{re.escape(term)}\b', combined_lower) for term in specific_terms)
            if not subject_found:
                return False  # Target substance/concept not in retrieved sources at all

        # If question asks about temperature: check if temperature numbers appear near fever
        if "temperature" in q_lower:
            temp_unit = r'\d+\.?\d*\s*(?:°c|celsius|degree|°f|fahrenheit)'
            if not re.search(temp_unit, combined_lower):
                return False
            # Check if temperature unit is associated with fever/contraindication
            fever_near_temp = (
                bool(re.search(rf'fever.{{0,100}}?{temp_unit}', combined_lower)) or
                bool(re.search(rf'{temp_unit}.{{0,100}}?fever', combined_lower))
            )
            if not fever_near_temp:
                return False

        # If question asks about dosage: check if numeric dose/volume appears near the subject
        if asks_dosage and specific_terms:
            dose_unit = r'\d+\.?\d*\s*(?:mg|ml|mcg|iu|drop|drops)'
            has_dose = False
            for term in specific_terms:
                if re.search(rf'\b{re.escape(term)}\b.{{0,150}}?{dose_unit}', combined_lower) or \
                   re.search(rf'{dose_unit}.{{0,150}}?\b{re.escape(term)}\b', combined_lower):
                    has_dose = True
                    break
            if not has_dose:
                return False

    return True


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

        # Rerank and select top chunks for focused LLM context
        selected = rerank_chunks(retrieval_query, chunks, max_chunks=2)
        if not selected:
            selected = chunks[:2]

        # Generic evidence sufficiency check — refuse early for quantitative
        # medical questions without explicit supporting evidence
        if not _has_sufficient_evidence(question, selected):
            return {
                "status": "insufficient_context",
                "answer": INSUFFICIENT_CONTEXT_MSG,
                "sources": [c.source_dict() for c in selected],
                "confidence": retrieval_confidence([c.similarity for c in selected]),
                "latency_ms": {"retrieval": retrieval_ms, "llm": 0,
                               "total": int((time.perf_counter() - t0) * 1000)},
            }

        prompt = build_prompt(question, selected, history=history)
        t1 = time.perf_counter()
        try:
            answer = self.llm.generate(prompt, system=SYSTEM_PROMPT).strip()
        except LLMError as e:
            # Surface the real error — never a fake answer (spec §23).
            return {
                "status": "error",
                "error": str(e),
                "answer": "",
                "sources": [c.source_dict() for c in selected],
                "confidence": 0.0,
                "latency_ms": {"retrieval": retrieval_ms, "llm": 0,
                               "total": int((time.perf_counter() - t0) * 1000)},
            }
        llm_ms = int((time.perf_counter() - t1) * 1000)

        is_refusal = (
            INSUFFICIENT_INFO_ANSWER in answer
            or "do not contain enough information" in answer.lower()
        )
        return {
            "status": "insufficient_context" if is_refusal else "ok",
            "answer": INSUFFICIENT_INFO_ANSWER if is_refusal else answer,
            "sources": [c.source_dict() for c in selected],
            "confidence": retrieval_confidence([c.similarity for c in selected]),
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