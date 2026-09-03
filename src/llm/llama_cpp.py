"""FUTURE on-device provider (llama.cpp / GGUF) — intentionally NOT implemented on Day 1.

This file exists to make the migration seam explicit: the RAG pipeline imports only
LLMProvider (src/llm/base.py), never Ollama. When the on-device runtime is chosen,
implement generate() here (llama-cpp-python or a QNN bridge), set LLM_PROVIDER=llama_cpp,
and nothing in src/rag, src/ingestion, main.py, or the output contract changes.
"""
from __future__ import annotations

from .base import LLMError, LLMProvider


class LlamaCppProvider(LLMProvider):
    name = "llama_cpp"

    def __init__(self, model_path: str, **_kwargs) -> None:
        raise LLMError(
            "LlamaCppProvider is planned for a later phase. Set LLM_PROVIDER=ollama for Day 1."
        )

    def generate(self, prompt: str, system: str | None = None) -> str:  # pragma: no cover
        raise LLMError("LlamaCppProvider is not implemented yet.")