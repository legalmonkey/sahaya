"""Persistent local ChromaDB wrapper (spec: §5/§9).

This store holds ONLY corpus RAG data. It never touches the shared household schema
(db/migrations/001_shared_schema.sql) — corpus data is deliberately kept separate.

Cosine space: chroma distance = 1 - cosine_similarity → similarity = 1 - distance.
Telemetry is disabled (chroma's posthog would otherwise be an external call).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

# Silence Chroma telemetry completely
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)

try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None


class VectorStore:
    def __init__(self, path: Path, collection_name: str) -> None:
        if chromadb is None:
            raise RuntimeError("chromadb is not installed. Please install requirements.txt.")
        path.mkdir(parents=True, exist_ok=True)
        self.path = Path(path)
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True, allow_reset=True),
        )
        self._col = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    @property
    def count(self) -> int:
        return self._col.count()

    def documents(self) -> list[str]:
        got = self._col.get(include=["metadatas"])
        return sorted({(m or {}).get("document", "") for m in got.get("metadatas") or []} - {""})

    def add_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        self._col.upsert(
            ids=[c["chunk_id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            embeddings=[c["embedding"] for c in chunks],
        )

    def delete_document(self, document: str) -> None:
        self._col.delete(where={"document": document})

    def clear(self) -> None:
        self._client.delete_collection(self._col.name)
        self._col = self._client.get_or_create_collection(
            name=self._col.name, metadata={"hnsw:space": "cosine"}
        )

    def query(self, embedding: list[float], n: int) -> list[dict]:
        total = self.count
        if total == 0 or n <= 0:
            return []
        res = self._col.query(
            query_embeddings=[embedding], n_results=min(n, total),
            include=["documents", "metadatas", "distances"],
        )
        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []
        out = []
        for i, cid in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            dist = dists[i] if i < len(dists) else 1.0
            out.append({
                "chunk_id": cid,
                "text": docs[i] if i < len(docs) else "",
                "document": (meta or {}).get("document", ""),
                "page": int((meta or {}).get("page", 0)),
                "section": (meta or {}).get("section") or None,
                "similarity": max(0.0, min(1.0, 1.0 - dist)),
            })
        return out

    def iter_chunks(self, batch: int = 500):
        """All chunks (id, text, metadata) — used by the TF-IDF baseline."""
        offset = 0
        while True:
            got = self._col.get(limit=batch, offset=offset,
                                include=["documents", "metadatas"])
            ids = got.get("ids") or []
            docs = got.get("documents") or []
            metas = got.get("metadatas") or []
            if not ids:
                break
            for i, cid in enumerate(ids):
                meta = metas[i] if i < len(metas) else {}
                yield {
                    "chunk_id": cid,
                    "text": docs[i] if i < len(docs) else "",
                    "document": (meta or {}).get("document", ""),
                    "page": int((meta or {}).get("page", 0)),
                    "section": (meta or {}).get("section") or None,
                }
            if len(ids) < batch:
                break
            offset += batch