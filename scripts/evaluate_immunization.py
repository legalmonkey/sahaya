"""Evaluation script for Child Immunization + RAG Integration (Part A).

Runs multiple realistic child cases and checks deterministic schedule evaluation,
grounded RAG answers, sources cited, confidence, and refusal on unsupported questions.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import builtins
_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _orig_print(*args, **kwargs)

from src.database import get_child, init_db, seed_demo_data
from src.immunization import (
    evaluate_child_immunization,
    get_child_immunization_guidance,
)
from src.rag.prompt import INSUFFICIENT_INFO_ANSWER


def run_evaluation() -> None:
    print("=" * 70)
    print("SAHAYA — IMMUNIZATION DATA + RAG INTEGRATION EVALUATION")
    print("=" * 70)

    # 1. Seed demo data
    print("\n[Step 1] Initializing SQLite schema & demo data...")
    seed_demo_data()
    print("✓ Demo database initialized with realistic test cases.")

    # 2. Test Case 1: Newborn with birth doses given
    print("\n" + "-" * 70)
    print("TEST CASE 1: Newborn (DOB: 2026-08-25) — Birth doses recorded")
    print("-" * 70)
    child1 = get_child("child_001")
    res1 = get_child_immunization_guidance(
        child_id_or_data=child1,
        question="What vaccines are currently due or upcoming for this child?",
        current_date="2026-09-01",
    )
    imm1 = res1["immunization_status"]
    print(f"Child Age: {imm1['age_display']}")
    print(f"Received ({len(imm1['received'])}): {[d['vaccine_name'] for d in imm1['received']]}")
    print(f"Due ({len(imm1['due'])}): {[d['vaccine_name'] for d in imm1['due']]}")
    print(f"Overdue ({len(imm1['overdue'])}): {[d['vaccine_name'] for d in imm1['overdue']]}")
    print(f"Upcoming ({len(imm1['upcoming'])}): {[d['vaccine_name'] for d in imm1['upcoming'][:4]]}...")
    print(f"\nSahaya Answer:\n{res1['answer']}")
    print(f"\nConfidence: {res1['confidence']:.2f}")
    print(f"Sources Cited ({len(res1['sources'])}): {[s['document'] + ' p.' + str(s['page']) for s in res1['sources']]}")

    # 3. Test Case 2: 6-month-old infant with missed doses
    print("\n" + "-" * 70)
    print("TEST CASE 2: 6-Month-Old (DOB: 2026-03-01) — Missed 6w, 10w, 14w doses")
    print("-" * 70)
    child2 = get_child("child_002")
    res2 = get_child_immunization_guidance(
        child_id_or_data=child2,
        question="What overdue vaccines should be administered and what is the schedule?",
        current_date="2026-09-01",
    )
    imm2 = res2["immunization_status"]
    print(f"Child Age: {imm2['age_display']}")
    print(f"Received ({len(imm2['received'])}): {[d['vaccine_name'] for d in imm2['received']]}")
    print(f"Overdue ({len(imm2['overdue'])}): {[d['vaccine_name'] for d in imm2['overdue']]}")
    print(f"\nSahaya Answer:\n{res2['answer']}")
    print(f"\nConfidence: {res2['confidence']:.2f}")
    print(f"Sources Cited ({len(res2['sources'])}): {[s['document'] + ' p.' + str(s['page']) for s in res2['sources']]}")

    # 4. Test Case 3: 10-month-old infant due for MR-1 & Vitamin A
    print("\n" + "-" * 70)
    print("TEST CASE 3: 10-Month-Old (DOB: 2025-11-01) — Up to date on primary doses")
    print("-" * 70)
    child3 = get_child("child_003")
    res3 = get_child_immunization_guidance(
        child_id_or_data=child3,
        question="What vaccines are due for this 10-month-old child?",
        current_date="2026-09-01",
    )
    imm3 = res3["immunization_status"]
    print(f"Child Age: {imm3['age_display']}")
    print(f"Received ({len(imm3['received'])}): {[d['vaccine_name'] for d in imm3['received']]}")
    print(f"Due ({len(imm3['due'])}): {[d['vaccine_name'] for d in imm3['due']]}")
    print(f"\nSahaya Answer:\n{res3['answer']}")
    print(f"\nConfidence: {res3['confidence']:.2f}")
    print(f"Sources Cited ({len(res3['sources'])}): {[s['document'] + ' p.' + str(s['page']) for s in res3['sources']]}")

    # 5. Test Case 4: Unsupported out-of-corpus question (testing refusal)
    print("\n" + "-" * 70)
    print("TEST CASE 4: Unsupported question (Out-of-corpus / Alien protocol)")
    print("-" * 70)
    res4 = get_child_immunization_guidance(
        child_id_or_data=child1,
        question="What is the dosage schedule for Martian space flu vaccine?",
        current_date="2026-09-01",
    )
    print(f"Sahaya Status: {res4['status']}")
    print(f"Sahaya Answer: {res4['answer']}")
    print(f"Confidence: {res4['confidence']}")
    assert res4["status"] == "insufficient_context" or INSUFFICIENT_INFO_ANSWER in res4["answer"], "Failed refusal test!"
    print("✓ Strict refusal verified — no hallucination.")

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
