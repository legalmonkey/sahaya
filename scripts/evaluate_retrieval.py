"""Evaluation script for retrieval accuracy and latency (spec: §13 / §17).

Evaluates the active retriever (Embedding or TF-IDF) against benchmark questions
from tests/questions.py without hardcoding any test strings in this file.

Usage:
  python scripts/evaluate_retrieval.py             # evaluate known protocol questions
  python scripts/evaluate_retrieval.py --all       # evaluate known + unseen questions
  python scripts/evaluate_retrieval.py --unseen    # evaluate only unseen questions
  python scripts/evaluate_retrieval.py --k 3       # override top_k
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import SETTINGS                                # noqa: E402
from src.rag.pipeline import retrieval_confidence              # noqa: E402
from src.rag.retriever import get_retriever                    # noqa: E402
from tests.questions import KNOWN_QUESTIONS, UNSEEN_QUESTIONS  # noqa: E402


def evaluate_queries(queries: list[str], retriever, k: int | None = None) -> dict:
    results = []
    total_latency_ms = 0.0
    total_sim = 0.0
    matched_count = 0

    print(f"\n{'#':<3} | {'Latency':<8} | {'Conf':<6} | {'Top Sim':<8} | {'Top Source':<35} | Query")
    print("-" * 100)

    for i, q in enumerate(queries, 1):
        t0 = time.perf_counter()
        chunks = retriever.retrieve(q, k=k)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        total_latency_ms += elapsed_ms

        sims = [c.similarity for c in chunks]
        conf = retrieval_confidence(sims)
        top_sim = sims[0] if sims else 0.0
        total_sim += top_sim

        if chunks:
            matched_count += 1
            top = chunks[0]
            sec = f":{top.section[:15]}" if top.section else ""
            source_desc = f"{top.document} (p.{top.page}{sec})"
        else:
            source_desc = "[NO CHUNKS RETRIEVED]"

        short_q = q if len(q) <= 45 else q[:42] + "..."
        print(f"{i:<3} | {elapsed_ms:>6.1f}ms | {conf:>6.2f} | {top_sim:>8.4f} | {source_desc:<35} | {short_q}")

        results.append({
            "query": q,
            "latency_ms": elapsed_ms,
            "confidence": conf,
            "top_similarity": top_sim,
            "chunk_count": len(chunks),
            "top_chunk": chunks[0].source_dict() if chunks else None,
        })

    n = max(1, len(queries))
    avg_latency = total_latency_ms / n
    avg_sim = total_sim / n
    coverage_pct = (matched_count / n) * 100.0

    print("-" * 100)
    print(f"Summary: {matched_count}/{len(queries)} retrieved ({coverage_pct:.1f}%) | "
          f"Avg Latency: {avg_latency:.1f}ms | Avg Top Sim: {avg_sim:.4f}")

    return {
        "results": results,
        "total_queries": len(queries),
        "matched_queries": matched_count,
        "coverage_pct": coverage_pct,
        "avg_latency_ms": avg_latency,
        "avg_top_similarity": avg_sim,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="run known and unseen benchmark questions")
    ap.add_argument("--unseen", action="store_true", help="run only unseen benchmark questions")
    ap.add_argument("--k", type=int, default=None, help="override top_k chunks retrieved")
    args = ap.parse_args()

    if args.unseen:
        queries = UNSEEN_QUESTIONS
        label = f"Unseen Questions ({len(queries)})"
    elif args.all:
        queries = KNOWN_QUESTIONS + UNSEEN_QUESTIONS
        label = f"All Questions ({len(queries)})"
    else:
        queries = KNOWN_QUESTIONS
        label = f"Known Questions ({len(queries)})"

    try:
        retriever = get_retriever()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to initialize retriever: {exc}")
        return 1

    print(f"Sahaya — Retrieval Evaluation")
    print(f"  Retriever: {retriever.name} (corpus chunks: {retriever.corpus_size})")
    print(f"  Benchmark: {label}")

    if retriever.corpus_size == 0:
        print(f"\nWARNING: Vector store is empty! Run `python scripts/ingest.py` first.")
        return 1

    summary = evaluate_queries(queries, retriever, k=args.k)
    return 0 if summary["matched_queries"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
