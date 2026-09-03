"""Central configuration. Every tunable lives here / in .env — never at call sites."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        # Strip inline comments (outside quotes)
        val = val.strip()
        if not (val.startswith('"') or val.startswith("'")):
            val = val.split("#", 1)[0].strip()
        os.environ.setdefault(key.strip(), val.strip('"').strip("'"))


_load_dotenv()


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _path(key: str, default: str) -> Path:
    p = Path(_get(key, default))
    return p if p.is_absolute() else ROOT / p


@dataclass(frozen=True)
class Settings:
    # corpus / storage
    raw_pdf_dir: Path = _path("RAW_PDF_DIR", "data/raw")
    vector_db_dir: Path = _path("VECTOR_DB_DIR", "data/vector_db")
    collection_name: str = _get("COLLECTION_NAME", "sahaya_chunks")

    # embeddings
    embedding_model: str = _get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_device: str = _get("EMBEDDING_DEVICE", "cpu")
    embedding_batch_size: int = int(_get("EMBEDDING_BATCH_SIZE", "32"))
    models_cache_dir: Path = _path("MODELS_CACHE_DIR", ".models")

    # retrieval
    retriever: str = _get("RETRIEVER", "embedding")          # embedding | tfidf
    top_k: int = int(_get("TOP_K", "5"))
    similarity_threshold: float = float(_get("SIMILARITY_THRESHOLD", "0.30"))
    tfidf_threshold: float = float(_get("TFIDF_THRESHOLD", "0.02"))

    # chunking
    chunk_max_words: int = int(_get("CHUNK_MAX_WORDS", "600"))
    chunk_min_words: int = int(_get("CHUNK_MIN_WORDS", "250"))
    chunk_overlap_sentences: int = int(_get("CHUNK_OVERLAP_SENTENCES", "2"))

    # LLM
    llm_provider: str = _get("LLM_PROVIDER", "ollama")
    llm_model: str = _get("LLM_MODEL", "llama3.1")
    ollama_host: str = _get("OLLAMA_HOST", "http://127.0.0.1:11434")
    llm_timeout_s: float = float(_get("LLM_TIMEOUT_S", "180"))
    llm_temperature: float = float(_get("LLM_TEMPERATURE", "0.1"))
    llm_num_ctx: int = int(_get("LLM_NUM_CTX", "2048"))


SETTINGS = Settings()