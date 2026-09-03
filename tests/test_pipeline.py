"""Unit tests for retrieval filtering, prompt construction, confidence, grounding
behaviour and error surfacing — all with FAKE retriever/LLM (no Ollama, no embeddings)."""
import pytest

from src.llm.base import LLMConnectionError, LLMError, LLMProvider
from src.rag.pipeline import INSUFFICIENT_CONTEXT_MSG, RAGPipeline, retrieval_confidence
from src.rag.prompt import SYSTEM_PROMPT, build_prompt
from src.rag.retriever import RetrievedChunk, Retriever


class FakeRetriever(Retriever):
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = 0

    def retrieve(self, query, k=None):
        self.calls += 1
        return list(self.chunks)


class FakeLLM(LLMProvider):
    def __init__(self, reply="grounded answer", error=None):
        self.reply, self.error = reply, error
        self.prompts = []

    def generate(self, prompt, system=None):
        self.prompts.append((system, prompt))
        if self.error:
            raise self.error
        return self.reply


def chunk(sim=0.8, doc="handbook.pdf", p=42, text="pentavalent schedule text"):
    return RetrievedChunk(text=text, document=doc, page=p, section="Schedule",
                          similarity=sim, chunk_id=f"{doc}::{p}")


def test_ok_answer_contains_sources_confidence_latency():
    r = FakeRetriever([chunk(0.8), chunk(0.7), chunk(0.5)])
    llm = FakeLLM()
    out = RAGPipeline(r, llm).answer_query("What is the pentavalent schedule?")
    assert out["status"] == "ok"
    assert out["answer"] == "grounded answer"
    assert len(out["sources"]) == 3
    assert out["sources"][0]["document"] == "handbook.pdf"
    assert out["sources"][0]["page"] == 42
    assert 0.5 <= out["confidence"] <= 0.8
    assert out["latency_ms"]["llm"] >= 0 and out["latency_ms"]["total"] >= 0

def test_prompt_contains_context_sources_and_question():
    c = chunk(text="BCG is given at birth on the left upper arm.")
    p = build_prompt("When is BCG given?", [c])
    assert "BCG is given at birth" in p
    assert "handbook.pdf" in p
    assert "42" in p
    assert "When is BCG given?" in p
    assert "only" in SYSTEM_PROMPT.lower() and "do not" in SYSTEM_PROMPT.lower()
    assert "who" in SYSTEM_PROMPT.lower() and "cdc" in SYSTEM_PROMPT.lower()


def test_system_prompt_forbids_outside_knowledge_and_orgs():
    sys_lower = SYSTEM_PROMPT.lower()
    assert "only the retrieved context" in sys_lower or "only using the retrieved context" in sys_lower
    assert "who" in sys_lower
    assert "cdc" in sys_lower
    assert "do not fill" in sys_lower or "do not use" in sys_lower


def test_build_prompt_structures_sources_cleanly():
    c1 = chunk(text="OPV zero dose at birth.", doc="nis.pdf", p=1)
    c2 = chunk(text="Pentavalent at 6 weeks.", doc="handbook.pdf", p=5)
    prompt = build_prompt("What vaccines at birth?", [c1, c2])
    assert "USER QUESTION:" in prompt
    assert "RETRIEVED SOURCES:" in prompt
    assert "SOURCE 1" in prompt
    assert "SOURCE 2" in prompt
    assert "Document: nis.pdf" in prompt
    assert "Document: handbook.pdf" in prompt
    assert "INSTRUCTIONS:" in prompt


def test_no_retrieval_means_no_llm_call():
    r = FakeRetriever([])
    llm = FakeLLM()
    out = RAGPipeline(r, llm).answer_query("anything")
    assert out["status"] == "insufficient_context"
    assert out["answer"] == INSUFFICIENT_CONTEXT_MSG
    assert out["sources"] == [] and out["confidence"] == 0.0
    assert llm.prompts == []          # the LLM is NEVER asked to answer from memory


def test_llm_error_is_surfaced_not_swallowed():
    r = FakeRetriever([chunk()])
    llm = FakeLLM(error=LLMConnectionError(
        "Ollama is not running or the configured model is unavailable."))
    out = RAGPipeline(r, llm).answer_query("q")
    assert out["status"] == "error"
    assert "Ollama is not running" in out["error"]
    assert out["answer"] == ""         # no fake answer


def test_confidence_is_derived_not_constant():
    assert retrieval_confidence([]) == 0.0
    assert retrieval_confidence([1.0, 1.0, 1.0]) == 1.0
    assert retrieval_confidence([0.9, 0.1]) == retrieval_confidence([0.1, 0.9])  # ordering irrelevant
    assert 0.0 <= retrieval_confidence([0.6, 0.4, 0.2]) <= 1.0


def test_empty_query_is_rejected():
    out = RAGPipeline(FakeRetriever([chunk()]), FakeLLM()).answer_query("   ")
    assert out["status"] == "error"