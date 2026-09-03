"""INTEGRATION test — requires a live local Ollama (auto-skipped otherwise)."""
import pytest

from src.config import SETTINGS
from src.llm.base import create_llm_provider


def _ollama_up() -> bool:
    try:
        import requests
        return requests.get(f"{SETTINGS.ollama_host}/api/tags", timeout=1).ok
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _ollama_up(), reason="Ollama not running (integration test)")


def test_provider_generate_and_health():
    provider = create_llm_provider()
    provider.health_check()
    out = provider.generate("Reply with the word OK and nothing else.",
                            system="You are a terse test assistant.")
    assert out and isinstance(out, str)