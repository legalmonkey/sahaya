"""Local embedding providers behind one interface (spec: §8) so the model can be
swapped for an on-device implementation later without touching retrieval."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import SETTINGS


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    name: str = "base"

    @abstractmethod
    def embed_texts(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """all-MiniLM-L6-v2 runs comfortably on CPU. First load downloads from HuggingFace
    ONCE; after that it is fully cached/offline (see README offline verification)."""

    name = "sentence-transformers"

    def __init__(self, model_name: str, device: str = "cpu",
                 batch_size: int = 32, cache_dir=None) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.cache_dir = str(cache_dir) if cache_dir else None
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers is not installed. Run: pip install -r requirements.txt"
            ) from e
        try:
            self._model = SentenceTransformer(
                self.model_name, device=self.device, cache_folder=self.cache_dir
            )
        except Exception as e:  # noqa: BLE001
            raise EmbeddingError(
                f"Failed to load embedding model '{self.model_name}'. If this is the first run, "
                f"the model must be downloaded once with network access; afterwards it is offline."
            ) from e

    def embed_texts(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_loaded()
        try:
            embs = self._model.encode(
                texts, batch_size=self.batch_size,
                normalize_embeddings=True, show_progress_bar=show_progress,
            )
        except Exception as e:  # noqa: BLE001
            raise EmbeddingError(f"Embedding failed: {e}") from e
        return [[float(x) for x in row] for row in embs]


_PROVIDER: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = SentenceTransformerEmbeddingProvider(
            SETTINGS.embedding_model, SETTINGS.embedding_device,
            SETTINGS.embedding_batch_size, SETTINGS.models_cache_dir,
        )
    return _PROVIDER