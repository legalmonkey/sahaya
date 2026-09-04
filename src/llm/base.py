"""LLM provider abstraction (spec: §10 / §19 / §20).

The RAG pipeline depends ONLY on LLMProvider. Day 1 ships OllamaProvider; a future
LlamaCppProvider (llama.cpp + GGUF) plugs into the same seam with zero RAG changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import SETTINGS


class LLMError(RuntimeError):
    pass


class LLMConnectionError(LLMError):
    pass


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        ...

    def health_check(self) -> None:
        """Raise LLMError if the provider is unusable. Default: no-op."""


def create_llm_provider(provider: str | None = None) -> LLMProvider:
    p = (provider if provider is not None else SETTINGS.llm_provider).lower()
    if p == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(
            host=SETTINGS.ollama_host, model=SETTINGS.llm_model,
            timeout_s=SETTINGS.llm_timeout_s, temperature=SETTINGS.llm_temperature,
            num_ctx=SETTINGS.llm_num_ctx,
        )
    if p == "llama_cpp":
        from .llama_cpp import LlamaCppProvider
        return LlamaCppProvider(
            model_path=SETTINGS.llama_cpp_model_path,
            n_ctx=SETTINGS.llama_cpp_n_ctx,
            n_threads=SETTINGS.llama_cpp_n_threads,
            temperature=SETTINGS.llm_temperature,
        )
    raise LLMError(f"Unknown LLM_PROVIDER '{p}' (supported: ollama, llama_cpp)")