#!/usr/bin/env python3
"""Sahaya — Protocol Assistant & Child Immunization CLI (spec: §12 / §16 / Part A).

Usage:
  python main.py                                      # interactive session
  python main.py "your question here"                 # one-shot general protocol question
  python main.py --child-id <id>                      # check child immunization status + guidance
  python main.py --child-id <id> --question "<q>"     # specific question for a child
  python main.py --seed-demo                          # initialize database with demo records
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)


import builtins
_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _orig_print(*args, **kwargs)


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def _print_result(res: dict) -> None:
    if res.get("status") == "error":
        print(f"\nERROR: {res.get('error')}")
        return

    # Print Immunization Status if present
    imm = res.get("immunization_status")
    if imm:
        print("\n" + "=" * 50)
        print(f"CHILD IMMUNIZATION RECORD ({res.get('child_id', 'N/A')})")
        print(f"  DOB: {imm.get('child_dob')}  |  Age: {res.get('age_display', imm.get('age_display'))}")
        print("-" * 50)

        rec = imm.get("received", [])
        print(f"  Received ({len(rec)}):")
        if rec:
            for d in rec:
                dt = f" on {d['date_given']}" if d.get("date_given") else ""
                print(f"    ✓ {d['vaccine_name']}{dt} ({d['recommended_age']})")
        else:
            print("    (None recorded)")

        due = imm.get("due", [])
        print(f"\n  Currently Due ({len(due)}):")
        if due:
            for d in due:
                print(f"    ➜ {d['vaccine_name']} (Recommended: {d['recommended_age']})")
        else:
            print("    (None)")

        overdue = imm.get("overdue", [])
        print(f"\n  OVERDUE / MISSED ({len(overdue)}):")
        if overdue:
            for d in overdue:
                print(f"    ⚠️ {d['vaccine_name']} (Overdue by {d.get('days_overdue', 0)} days — Rec: {d['recommended_age']})")
        else:
            print("    (None)")

        upcoming = imm.get("upcoming", [])
        if upcoming:
            next_doses = upcoming[:3]
            print(f"\n  Upcoming Milestones:")
            for d in next_doses:
                print(f"    • {d['vaccine_name']} at {d['recommended_age']}")
        print("=" * 50)

    print("\nSahaya Guidance:")
    print(res.get("answer") or "(No answer generated)")

    sources = res.get("sources") or []
    if sources:
        print("\nSources Cited:")
        for i, s in enumerate(sources, 1):
            sec = f" — {s['section']}" if s.get("section") else ""
            sim_str = f"  (similarity {s['similarity']:.2f})" if "similarity" in s else ""
            print(f" {i}. {s['document']} — page {s['page']}{sec}{sim_str}")

    print(f"\nConfidence: {res.get('confidence', 0.0):.2f}  "
          f"(retrieval confidence — how well the corpus matched; NOT medical certainty)")
    lat = res.get("latency_ms", {})
    if lat:
        print(f"Latency: retrieval {lat.get('retrieval', 0)} ms · "
              f"LLM {lat.get('llm', 0)} ms · total {lat.get('total', 0)} ms")


def main() -> int:
    try:
        from src.config import SETTINGS
        from src.database import init_db, seed_demo_data
        from src.immunization import get_child_immunization_guidance
        from src.llm.base import LLMError
        from src.rag.pipeline import answer_query, corpus_stats, get_pipeline
    except Exception as e:  # noqa: BLE001
        _fail(f"import failed — install dependencies first ({e})\n  pip install -r requirements.txt")

    parser = argparse.ArgumentParser(description="Sahaya Offline Health Assistant CLI")
    parser.add_argument("query", nargs="*", help="Optional general protocol question")
    parser.add_argument("--child-id", dest="child_id", default=None, help="Child record ID to inspect and query")
    parser.add_argument("--question", dest="question", default=None, help="Specific question about child's immunization")
    parser.add_argument("--seed-demo", dest="seed_demo", action="store_true", help="Seed database with demo records")

    args = parser.parse_args()

    # Handle --seed-demo
    if args.seed_demo:
        seed_demo_data()
        print(f"Database seeded successfully at {SETTINGS.database_path}.")
        return 0

    # Ensure DB is initialized
    try:
        init_db()
    except Exception as e:
        print(f"Warning: database initialization notice: {e}")

    stats = corpus_stats()
    if stats["chunks"] == 0:
        _fail(f"vector store is empty. Place PDFs in {SETTINGS.raw_pdf_dir} and run: python scripts/ingest.py")

    # Handle child immunization mode
    if args.child_id:
        try:
            get_pipeline().llm.health_check()
        except LLMError as e:
            _fail(str(e))

        default_q = "What vaccines are due for this child and what is the schedule for overdue doses?"
        question = args.question or (" ".join(args.query) if args.query else default_q)
        res = get_child_immunization_guidance(args.child_id, question=question)
        _print_result(res)
        return 0

    # Handle one-shot question
    if args.query:
        try:
            get_pipeline().llm.health_check()
        except LLMError as e:
            _fail(str(e))
        _print_result(answer_query(" ".join(args.query)))
        return 0

    # Interactive session
    llm_info = f"{SETTINGS.llm_provider}/{SETTINGS.llm_model}"
    if SETTINGS.llm_provider == "ollama":
        llm_info += f" @ {SETTINGS.ollama_host}"
    elif SETTINGS.llm_provider == "llama_cpp":
        llm_info += f" (GGUF: {SETTINGS.llama_cpp_model_path or 'Not configured'})"

    print("Sahaya — Protocol & Child Immunization CLI")
    print(f"  LLM:       {llm_info}")
    print(f"  Retrieval: {SETTINGS.retriever} · top_k={SETTINGS.top_k} · threshold={SETTINGS.similarity_threshold}")
    print(f"  Corpus:    {stats['chunks']} chunks from {len(stats['documents'])} document(s)")
    print(f"  Database:  {SETTINGS.database_path}")

    try:
        get_pipeline().llm.health_check()
    except LLMError as e:
        _fail(str(e))

    from src.rag import ConversationBuffer
    buffer = ConversationBuffer()
    active_child_id: str | None = None

    print("\nCommands: 'child <id>' | 'reset' / 'clear' | 'quit'")
    print("Type your questions below for multi-turn protocol assistance.")

    while True:
        try:
            prompt_label = f"\nAsk Sahaya [{active_child_id}]: " if active_child_id else "\nAsk Sahaya: "
            q = input(prompt_label).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if q.lower() in {"quit", "exit"}:
            return 0
        if not q:
            continue
        if q.lower() in {"reset", "clear"}:
            buffer.clear()
            active_child_id = None
            print("Conversation context and active child reset.")
            continue
        if q.lower().startswith("child "):
            cid = q.split(maxsplit=1)[1].strip()
            active_child_id = cid
            res = get_child_immunization_guidance(cid, history=buffer)
            _print_result(res)
            if res.get("status") == "ok":
                buffer.add_turn(q, res.get("answer", ""), sources=res.get("sources", []), context=res.get("immunization_status"))
        else:
            if active_child_id:
                res = get_child_immunization_guidance(active_child_id, question=q, history=buffer)
            else:
                res = answer_query(q, history=buffer)
            _print_result(res)
            if res.get("status") == "ok":
                buffer.add_turn(q, res.get("answer", ""), sources=res.get("sources", []), context=res.get("immunization_status"))


if __name__ == "__main__":
    raise SystemExit(main())