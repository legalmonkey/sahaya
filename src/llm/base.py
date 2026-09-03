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


def create_llm_provider() -> LLMProvider:
    provider = SETTINGS.llm_provider.lower()
    if provider == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(
            host=SETTINGS.ollama_host, model=SETTINGS.llm_model,
            timeout_s=SETTINGS.llm_timeout_s, temperature=SETTINGS.llm_temperature,
            num_ctx=SETTINGS.llm_num_ctx,
        )
    if provider == "llama_cpp":
        from .llama_cpp import LlamaCppProvider
        return LlamaCppProvider(SETTINGS.llm_model)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (supported: ollama; llama_cpp planned)")