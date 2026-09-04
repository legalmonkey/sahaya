"""Real llama.cpp end-to-end RAG validation script (Part A validation).

Executes the official Sahaya RAG pipeline against a local GGUF model via LlamaCppProvider.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Enforce strict offline settings
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from src.config import SETTINGS
from src.llm.llama_cpp import LlamaCppProvider
from src.rag import ConversationBuffer, RAGPipeline, get_retriever


def validate_real_llamacpp(model_path: str | Path) -> None:
    p = Path(model_path)
    model_file = p if p.is_absolute() else ROOT / p
    if not model_file.exists():
        print(f"ERROR: Model file not found at {model_file}")
        sys.exit(1)

    print("=" * 70)
    print("SAHAYA REAL LLAMA.CPP VALIDATION")
    print(f"Model File:    {model_file}")
    print(f"Model Size:    {model_file.stat().st_size / (1024 * 1024):.1f} MB")
    print("=" * 70)

    # 1. Initialize provider and measure model load time
    t_load_0 = time.perf_counter()
    provider = LlamaCppProvider(
        model_path=model_file,
        n_ctx=SETTINGS.llama_cpp_n_ctx,
        n_threads=SETTINGS.llama_cpp_n_threads,
        temperature=SETTINGS.llm_temperature,
    )
    provider.health_check()
    # Force initial model load
    provider._ensure_loaded()
    load_time_ms = int((time.perf_counter() - t_load_0) * 1000)
    print(f"\n[1] Llama.cpp Model Loaded in {load_time_ms} ms")

    # 2. Build Pipeline
    retriever = get_retriever()
    pipeline = RAGPipeline(retriever, provider)

    test_queries = [
        ("A. Grounded Protocol Query", "What vaccines are given at birth?"),
        ("B. Grounded Schedule Query", "What vaccines are given at 6 weeks?"),
        ("C. Unsupported Fever Question (Expect Refusal)", "What exact temperature of fever prevents vaccination?"),
        ("D. Unsupported Paracetamol Question (Expect Refusal)", "What is the dosage of paracetamol for a child?"),
    ]

    print("\n" + "=" * 70)
    print("SINGLE-TURN PROTOCOL & GROUNDING TESTS")
    print("=" * 70)

    for label, query in test_queries:
        print(f"\n>>> [{label}]")
        print(f"Question: {query}")
        t0 = time.perf_counter()
        res = pipeline.answer_query(query)
        total_time_ms = int((time.perf_counter() - t0) * 1000)

        print(f"Status:     {res.get('status')}")
        print(f"Confidence: {res.get('confidence', 0.0):.2f}")
        print(f"Sources:    {len(res.get('sources', []))} chunks")
        for i, s in enumerate(res.get("sources", [])[:3], 1):
            print(f"  - Source {i}: {s['document']} (page {s['page']}, similarity {s['similarity']:.2f})")
        print(f"Latency:    Retrieval {res.get('latency_ms', {}).get('retrieval', 0)} ms | LLM {res.get('latency_ms', {}).get('llm', 0)} ms | Total {total_time_ms} ms")
        print(f"Answer:\n{res.get('answer')}")
        print("-" * 50)

    # 3. Multi-Turn Test
    print("\n" + "=" * 70)
    print("MULTI-TURN TEST WITH REAL LLAMA.CPP")
    print("=" * 70)
    buffer = ConversationBuffer(max_turns=2)

    turn1_q = "What vaccines are given at birth?"
    print(f"\nTurn 1 Question: {turn1_q}")
    res1 = pipeline.answer_query(turn1_q, history=buffer)
    print(f"Turn 1 Answer:\n{res1.get('answer')}")
    buffer.add_turn(turn1_q, res1.get("answer", ""), sources=res1.get("sources", []))

    turn2_q = "What about the second dose?"
    print(f"\nTurn 2 Question: {turn2_q}")
    res2 = pipeline.answer_query(turn2_q, history=buffer)
    print(f"Turn 2 Status:     {res2.get('status')}")
    print(f"Turn 2 Sources:    {len(res2.get('sources', []))} chunks cited")
    for i, s in enumerate(res2.get("sources", [])[:2], 1):
        print(f"  - Source {i}: {s['document']} (page {s['page']})")
    print(f"Turn 2 Answer:\n{res2.get('answer')}")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = os.environ.get("LLAMA_CPP_MODEL_PATH", "data/models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
    validate_real_llamacpp(target_path)
