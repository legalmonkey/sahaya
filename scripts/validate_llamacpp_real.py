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
        print(f"ERROR: Model file not found at {model_file}", flush=True)
        sys.exit(1)

    print("=" * 70, flush=True)
    print("SAHAYA REAL LLAMA.CPP VALIDATION", flush=True)
    print(f"Model File:    {model_file}", flush=True)
    print(f"Model Size:    {model_file.stat().st_size / (1024 * 1024):.1f} MB", flush=True)
    print("=" * 70, flush=True)

    # 1. Initialize provider and measure model load time
    print("\n[Step 1/3] Loading Llama.cpp model into memory...", flush=True)
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
    print(f"✓ Model loaded successfully in {load_time_ms} ms (threads: {provider.n_threads}, ctx: {provider.n_ctx})\n", flush=True)

    # 2. Build Pipeline
    retriever = get_retriever()
    pipeline = RAGPipeline(retriever, provider)

    test_queries = [
        ("A. Grounded Protocol Query", "What vaccines are given at birth?"),
        ("B. Grounded Schedule Query", "What vaccines are given at 6 weeks?"),
        ("C. Unsupported Fever Question (Expect Refusal)", "What exact temperature of fever prevents vaccination?"),
        ("D. Unsupported Paracetamol Question (Expect Refusal)", "What is the dosage of paracetamol for a child?"),
    ]

    print("=" * 70, flush=True)
    print("SINGLE-TURN PROTOCOL & GROUNDING TESTS", flush=True)
    print("=" * 70, flush=True)

    for i, (label, query) in enumerate(test_queries, 1):
        print(f"\n[{i}/4] Query: {label}", flush=True)
        print(f"Question: \"{query}\"", flush=True)
        print("  -> Retrieving corpus chunks & generating grounded answer...", flush=True)
        t0 = time.perf_counter()
        res = pipeline.answer_query(query)
        total_time_ms = int((time.perf_counter() - t0) * 1000)

        print(f"  Status:     {res.get('status')}", flush=True)
        print(f"  Confidence: {res.get('confidence', 0.0):.2f}", flush=True)
        print(f"  Sources:    {len(res.get('sources', []))} chunks cited", flush=True)
        for idx, s in enumerate(res.get("sources", [])[:3], 1):
            print(f"    - Source {idx}: {s['document']} (page {s['page']}, similarity {s['similarity']:.2f})", flush=True)
        print(f"  Latency:    Retrieval {res.get('latency_ms', {}).get('retrieval', 0)} ms | LLM {res.get('latency_ms', {}).get('llm', 0)} ms | Total {total_time_ms} ms", flush=True)
        print(f"  Answer:\n{res.get('answer')}", flush=True)
        print("-" * 50, flush=True)

    # 3. Multi-Turn Test
    print("\n" + "=" * 70, flush=True)
    print("MULTI-TURN TEST WITH REAL LLAMA.CPP", flush=True)
    print("=" * 70, flush=True)
    buffer = ConversationBuffer(max_turns=2)

    turn1_q = "What vaccines are given at birth?"
    print(f"\nTurn 1 Question: \"{turn1_q}\"", flush=True)
    print("  -> Generating Turn 1...", flush=True)
    res1 = pipeline.answer_query(turn1_q, history=buffer)
    print(f"  Turn 1 Answer:\n{res1.get('answer')}", flush=True)
    buffer.add_turn(turn1_q, res1.get("answer", ""), sources=res1.get("sources", []))

    turn2_q = "What about the second dose?"
    print(f"\nTurn 2 Follow-up Question: \"{turn2_q}\"", flush=True)
    print("  -> Contextualizing query with Turn 1 and generating...", flush=True)
    res2 = pipeline.answer_query(turn2_q, history=buffer)
    print(f"  Turn 2 Status:     {res2.get('status')}", flush=True)
    print(f"  Turn 2 Sources:    {len(res2.get('sources', []))} chunks cited", flush=True)
    for idx, s in enumerate(res2.get("sources", [])[:2], 1):
        print(f"    - Source {idx}: {s['document']} (page {s['page']})", flush=True)
    print(f"  Turn 2 Answer:\n{res2.get('answer')}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("REAL LLAMA.CPP VALIDATION COMPLETED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = os.environ.get("LLAMA_CPP_MODEL_PATH", "data/models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
    validate_real_llamacpp(target_path)
