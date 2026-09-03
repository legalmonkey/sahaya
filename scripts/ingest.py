"""Ingestion script (spec: §4).

Usage:
  python scripts/ingest.py                # ingest new/changed PDFs from data/raw/
  python scripts/ingest.py --rebuild      # wipe the vector store and re-ingest everything
  python scripts/ingest.py --dir sources  # override the corpus folder

Idempotent: files are hashed (sha256); unchanged files are skipped, changed files are
re-ingested (their old chunks are deleted first). The store persists between runs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import SETTINGS                                    # noqa: E402
from src.ingestion.chunker import chunk_document                   # noqa: E402
from src.ingestion.embedder import get_embedding_provider          # noqa: E402
from src.ingestion.pdf_loader import (                             # noqa: E402
    PdfExtractionError, discover_pdfs, extract_pages, file_sha256,
)
from src.rag.store import VectorStore                              # noqa: E402


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true", help="clear the store first")
    ap.add_argument("--dir", default=None, help="PDF folder override (default: RAW_PDF_DIR)")
    args = ap.parse_args()

    folder = Path(args.dir).resolve() if args.dir else SETTINGS.raw_pdf_dir
    store = VectorStore(SETTINGS.vector_db_dir, SETTINGS.collection_name)
    manifest_path = store.path / "manifest.json"
    manifest = load_manifest(manifest_path)
    if args.rebuild:
        store.clear()
        manifest = {}
        print("[rebuild] vector store cleared")

    pdfs = discover_pdfs(folder)
    if not pdfs:
        print(f"No PDFs found in {folder}. Place official government PDFs there "
              f"(or set RAW_PDF_DIR / use --dir).")
        return 1

    embedder = get_embedding_provider()
    failures: list[str] = []
    all_word_counts: list[int] = []
    sections_found = 0

    for pdf in pdfs:
        sha = file_sha256(pdf)
        if manifest.get(pdf.name, {}).get("sha256") == sha:
            print(f"[skip]   {pdf.name} (unchanged since last ingest)")
            continue
        try:
            pages = extract_pages(pdf)
        except PdfExtractionError as e:
            print(f"[FAIL]   {e}")
            failures.append(str(e))
            continue

        chunks = chunk_document(
            pages, pdf.name,
            max_words=SETTINGS.chunk_max_words,
            min_words=SETTINGS.chunk_min_words,
            overlap_sentences=SETTINGS.chunk_overlap_sentences,
        )
        if not chunks:
            print(f"[FAIL]   {pdf.name}: extraction produced no usable chunks")
            failures.append(f"{pdf.name}: no usable chunks")
            continue

        print(f"[ingest] {pdf.name}: {len(pages)} pages -> {len(chunks)} chunks "
              f"(embedding {SETTINGS.embedding_model})")
        t0 = time.perf_counter()
        embeddings = embedder.embed_texts([c["text"] for c in chunks], show_progress=True)
        for c, e in zip(chunks, embeddings):
            c["embedding"] = e
        if pdf.name in store.documents():
            store.delete_document(pdf.name)
        store.add_chunks(chunks)
        print(f"         stored in {time.perf_counter() - t0:.1f}s "
              f"(store now holds {store.count} chunks)")

        all_word_counts += [len(c["text"].split()) for c in chunks]
        sections_found += sum(1 for c in chunks if c["metadata"]["section"])
        manifest[pdf.name] = {
            "sha256": sha, "pages": len(pages), "chunks": len(chunks),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        save_manifest(manifest_path, manifest)

    if all_word_counts:
        avg = sum(all_word_counts) / len(all_word_counts)
        print(f"\nSummary: {len(store.documents())} documents · {store.count} chunks · "
              f"words/chunk min {min(all_word_counts)} · avg {avg:.0f} · max {max(all_word_counts)} "
              f"(target {SETTINGS.chunk_min_words}-{SETTINGS.chunk_max_words}) · "
              f"sections identified for {sections_found}/{len(all_word_counts)} chunks "
              f"(null = honestly unknown, never invented)")
    if failures:
        print("\nFAILED documents (surfaced, not hidden):")
        for f in failures:
            print(f"  - {f}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())