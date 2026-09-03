#!/usr/bin/env python3
"""Sahaya — Day 1 CLI demo (spec: §12 / §16).

Usage:
  python main.py                          # interactive session
  python main.py "your question here"     # one-shot
"""
from __future__ import annotations

import logging
import os
import sys

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def _print_result(res: dict) -> None:
    if res.get("status") == "error":
        print(f"\nERROR: {res.get('error')}")
        return
    print("\nSahaya:")
    print(res["answer"])

    sources = res.get("sources") or []
    if sources:
        print("\nSources:")
        for i, s in enumerate(sources, 1):
            sec = f" — {s['section']}" if s.get("section") else ""
            print(f" {i}. {s['document']} — page {s['page']}{sec}  (similarity {s['similarity']:.2f})")
    print(f"\nConfidence: {res['confidence']:.2f}  "
          f"(retrieval confidence — how well the corpus matched; NOT medical certainty)")
    lat = res.get("latency_ms", {})
    print(f"Latency: retrieval {lat.get('retrieval', 0)} ms · "
          f"LLM {lat.get('llm', 0)} ms · total {lat.get('total', 0)} ms")


def main() -> int:
    try:
        from src.config import SETTINGS
        from src.llm.base import LLMError
        from src.rag.pipeline import answer_query, corpus_stats, get_pipeline
    except Exception as e:  # noqa: BLE001
        _fail(f"import failed — install dependencies first ({e})\n  pip install -r requirements.txt")

    print("Sahaya — Day 1 RAG CLI")
    print(f"  LLM:       {SETTINGS.llm_provider}/{SETTINGS.llm_model} @ {SETTINGS.ollama_host}")
    print(f"  Retrieval: {SETTINGS.retriever} · top_k={SETTINGS.top_k} · "
          f"threshold={SETTINGS.similarity_threshold}")
    stats = corpus_stats()
    print(f"  Corpus:    {stats['chunks']} chunks from {len(stats['documents'])} document(s)")

    if stats["chunks"] == 0:
        _fail(f"vector store is empty. Place PDFs in {SETTINGS.raw_pdf_dir} and run: "
              f"python scripts/ingest.py")
    try:
        get_pipeline().llm.health_check()
    except LLMError as e:
        _fail(str(e))

    if len(sys.argv) > 1:
        _print_result(answer_query(" ".join(sys.argv[1:])))
        return 0

    print("\nType a question ('quit' to exit).")
    while True:
        try:
            q = input("\nAsk Sahaya: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if q.lower() in {"quit", "exit"}:
            return 0
        if not q:
            continue
        _print_result(answer_query(q))


if __name__ == "__main__":
    raise SystemExit(main())