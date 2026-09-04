"""On-device LLM provider using llama.cpp and local GGUF models (spec: §10 / §19 / §20).

Operates 100% offline with zero external network requests and no automatic model downloads.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..config import ROOT
from .base import LLMError, LLMProvider


class LlamaCppProvider(LLMProvider):
    name = "llama_cpp"

    def __init__(
        self,
        model_path: str | Path | None = None,
        n_ctx: int = 8192,
        n_threads: int | None = None,
        temperature: float = 0.1,
        repeat_penalty: float = 1.15,
        max_tokens: int = 200,
    ) -> None:
        if model_path:
            p = Path(model_path)
            self.model_path = p if p.is_absolute() else ROOT / p
        else:
            self.model_path = None
        self.n_ctx = n_ctx
        self.n_threads = n_threads if n_threads is not None else max(4, os.cpu_count() or 4)
        self.temperature = temperature
        self.repeat_penalty = repeat_penalty
        self.max_tokens = max_tokens
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        if not self.model_path:
            raise LLMError(
                "LLAMA_CPP_MODEL_PATH is not configured. "
                "Please set LLAMA_CPP_MODEL_PATH in your environment or .env to a valid local GGUF model file."
            )

        if not self.model_path.exists():
            raise LLMError(
                f"Llama.cpp GGUF model file not found at '{self.model_path}'. "
                "Please ensure the local GGUF file exists and is accessible."
            )

        try:
            import llama_cpp
        except ImportError as e:
            raise LLMError(
                "llama-cpp-python is not installed. To use LLM_PROVIDER=llama_cpp, "
                "please install the python package (e.g. pip install llama-cpp-python)."
            ) from e

        try:
            self._model = llama_cpp.Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_batch=512,
                verbose=False,
            )
        except Exception as e:
            raise LLMError(
                f"Failed to load GGUF model from '{self.model_path}': {e}"
            ) from e

    def generate(self, prompt: str, system: str | None = None) -> str:
        self._ensure_loaded()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            if hasattr(self._model, "create_chat_completion"):
                try:
                    res = self._model.create_chat_completion(
                        messages=messages,
                        temperature=self.temperature,
                        repeat_penalty=self.repeat_penalty,
                        max_tokens=self.max_tokens,
                    )
                except ValueError as ve:
                    if "system" in str(ve).lower():
                        # Models like Gemma do not support a separate system role in their chat template
                        merged_content = f"{system}\n\n{prompt}" if system else prompt
                        res = self._model.create_chat_completion(
                            messages=[{"role": "user", "content": merged_content}],
                            temperature=self.temperature,
                            repeat_penalty=self.repeat_penalty,
                            max_tokens=self.max_tokens,
                        )
                    else:
                        raise
                content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                formatted_prompt = f"{system}\n\nUser: {prompt}\nAssistant:" if system else prompt
                res = self._model(
                    formatted_prompt,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty,
                    max_tokens=self.max_tokens,
                    stop=["User:", "\n\n\n"],
                )
                content = res.get("choices", [{}])[0].get("text", "")
        except Exception as e:
            raise LLMError(f"llama.cpp generation failed: {e}") from e

        if not content or not content.strip():
            raise LLMError("llama.cpp returned an empty response.")
        return content.strip()

    def health_check(self) -> None:
        if not self.model_path:
            raise LLMError(
                "LLAMA_CPP_MODEL_PATH is not configured. "
                "Set LLAMA_CPP_MODEL_PATH to a valid local GGUF model file."
            )
        if not self.model_path.exists():
            raise LLMError(
                f"Llama.cpp GGUF model file not found at '{self.model_path}'."
            )