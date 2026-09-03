"""Ollama provider — local HTTP to the Ollama daemon. Development runtime only (spec §1)."""
from __future__ import annotations

import requests

from .base import LLMConnectionError, LLMError, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str, model: str, timeout_s: float = 180.0,
                 temperature: float = 0.1, num_ctx: int = 8192) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.num_ctx = num_ctx

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        try:
            r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout_s)
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(
                f"Ollama is not running or unreachable at {self.host}. Start it with: ollama serve"
            ) from e
        except requests.exceptions.Timeout as e:
            raise LLMError(
                f"Ollama timed out after {self.timeout_s:.0f}s (model: {self.model})."
            ) from e
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ollama request failed: {e}") from e

        if r.status_code == 404 or (r.ok and "error" in r.json()):
            return _model_error(r, self.model)
        if not r.ok:
            raise LLMError(f"Ollama returned HTTP {r.status_code}: {r.text[:300]}")
        try:
            content = r.json().get("message", {}).get("content", "")
        except ValueError as e:
            raise LLMError(f"Ollama returned invalid JSON: {r.text[:300]}") from e
        if not content.strip():
            raise LLMError("Ollama returned an empty response.")
        return content.strip()

    def health_check(self) -> None:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=3)
        except requests.exceptions.RequestException as e:
            raise LLMConnectionError(
                f"Ollama is not running or unreachable at {self.host}. Start it with: ollama serve"
            ) from e
        if r.status_code != 200:
            raise LLMError(f"Ollama at {self.host} returned HTTP {r.status_code}.")
        models = [m.get("name", "") for m in r.json().get("models", [])]
        if not any(m == self.model or m.split(":")[0] == self.model for m in models):
            raise LLMError(
                f"Model '{self.model}' is unavailable in Ollama. Run: ollama pull {self.model}"
            )


def _model_error(r, model: str) -> str:
    detail = ""
    try:
        detail = r.json().get("error", "")
    except ValueError:
        pass
    raise LLMError(
        f"Model '{model}' is not available in Ollama ({detail}). Run: ollama pull {model}"
    )