"""Tests for RAG grounding and anti-hallucination guardrails (spec: §10).

Ensures:
1. System prompt strictly forbids using ungrounded external knowledge (WHO, CDC, unmentioned rules).
2. Prompt formats each source distinctly so the LLM can only ground on provided chunks.
3. When retrieval yields no evidence, pipeline returns insufficient_context without invoking the LLM.
4. Response source attribution comes strictly from retrieved chunks, preventing source hallucination.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.llm.base import LLMProvider
from src.rag.pipeline import INSUFFICIENT_CONTEXT_MSG, RAGPipeline
from src.rag.prompt import INSUFFICIENT_INFO_ANSWER, SYSTEM_PROMPT, build_prompt
from src.rag.retriever import RetrievedChunk, Retriever


class MockRetriever(Retriever):
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        return list(self.chunks)


class RecordingLLM(LLMProvider):
    def __init__(self, answer: str = "Grounded response.") -> None:
        self.answer = answer
        self.last_prompt = ""
        self.last_system = ""
        self.call_count = 0

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system = system or ""
        return self.answer


def test_system_prompt_forbids_external_organizations_and_assumptions():
    sys_prompt = SYSTEM_PROMPT.lower()
    assert "who" in sys_prompt
    assert "cdc" in sys_prompt
    assert "do not use" in sys_prompt or "must answer using only" in sys_prompt
    assert "the available sahaya sources do not contain enough information" in sys_prompt


def test_build_prompt_explicitly_labels_sources_and_instructions():
    chunk = RetrievedChunk(
        text="BCG is administered as a single dose of 0.1 ml at birth.",
        document="Immunization_Handbook.pdf",
        page=12,
        section="1.2 BCG Administration",
        similarity=0.85,
        chunk_id="bcg_chunk_1",
    )
    prompt = build_prompt("What is the BCG dose?", [chunk])

    assert "USER QUESTION:" in prompt
    assert "What is the BCG dose?" in prompt
    assert "RETRIEVED SOURCES:" in prompt
    assert "SOURCE 1" in prompt
    assert "Document: Immunization_Handbook.pdf" in prompt
    assert "Page: 12" in prompt
    assert "Section: 1.2 BCG Administration" in prompt
    assert "Content:" in prompt
    assert "BCG is administered as a single dose of 0.1 ml at birth." in prompt
    assert "INSTRUCTIONS:" in prompt
    assert INSUFFICIENT_INFO_ANSWER in prompt


def test_insufficient_evidence_returns_safe_message_without_llm_call():
    retriever = MockRetriever([])
    llm = RecordingLLM()
    pipeline = RAGPipeline(retriever, llm)

    result = pipeline.answer_query("What is the protocol for an unknown condition?")

    assert result["status"] == "insufficient_context"
    assert result["answer"] == INSUFFICIENT_CONTEXT_MSG
    assert result["sources"] == []
    assert result["confidence"] == 0.0
    assert llm.call_count == 0  # Crucial: LLM must NEVER be called when retrieval finds no evidence


def test_sources_in_output_match_retrieved_chunks_not_llm_hallucinations():
    c1 = RetrievedChunk(
        text="OPV zero dose is given at birth.",
        document="UIP_Schedule.pdf",
        page=1,
        section="Birth Doses",
        similarity=0.78,
        chunk_id="opv_0",
    )
    retriever = MockRetriever([c1])
    # Even if LLM text mentions outside names, application-level source attribution is strictly retrieved chunks
    llm = RecordingLLM(answer="OPV zero dose is given at birth.")
    pipeline = RAGPipeline(retriever, llm)

    result = pipeline.answer_query("When is OPV zero dose given?")

    assert result["status"] == "ok"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["document"] == "UIP_Schedule.pdf"
    assert result["sources"][0]["page"] == 1
    assert result["sources"][0]["similarity"] == 0.78
