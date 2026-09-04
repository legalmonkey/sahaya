"""RAG integration layer for child immunization status and protocol guidance (Part A).

Connects child vaccination records to the existing grounded RAG system, retrieving
official corpus chunks and answering user questions with strict grounding and source attribution.
"""
from __future__ import annotations

import datetime
from typing import Any

from ..database import get_child
from ..rag.pipeline import RAGPipeline, answer_query, get_pipeline
from .service import ImmunizationError, ImmunizationStatus, evaluate_child_immunization


def _build_contextual_query(
    question: str,
    status: ImmunizationStatus,
) -> str:
    """Build a search-friendly query string to retrieve relevant corpus guidelines."""
    q_lower = question.lower()
    
    # Extract vaccine names mentioned in due/overdue
    due_names = [d["vaccine_name"] for d in status.due]
    overdue_names = [d["vaccine_name"] for d in status.overdue]
    target_vaccines = due_names + overdue_names

    parts = [question.strip()]
    if target_vaccines and any(kw in q_lower for kw in ("due", "schedule", "vaccine", "what", "next", "missed", "overdue")):
        v_str = ", ".join(target_vaccines[:4])
        parts.append(f"National Immunization Schedule guidelines for child age {status.age_display}: {v_str}")

    return " ".join(parts)


def _build_augmented_question_for_rag(
    question: str,
    status: ImmunizationStatus,
) -> str:
    """Provide the child's factual immunization status to the grounded prompt."""
    rec_str = ", ".join(d["vaccine_name"] for d in status.received) or "None recorded"
    due_str = ", ".join(d["vaccine_name"] for d in status.due) or "None"
    overdue_str = ", ".join(f"{d['vaccine_name']} (overdue by {d.get('days_overdue', 0)} days)" for d in status.overdue) or "None"

    context_summary = (
        f"Child Status: Age = {status.age_display} (DOB: {status.child_dob}). "
        f"Received vaccines: [{rec_str}]. "
        f"Currently due: [{due_str}]. "
        f"Overdue: [{overdue_str}].\n"
        f"Worker Question: {question.strip()}"
    )
    return context_summary


def get_child_immunization_guidance(
    child_id_or_data: str | dict[str, Any],
    question: str = "What vaccines are due for this child and what is the protocol for overdue doses?",
    current_date: str | datetime.date | None = None,
    history: Any | None = None,
    pipeline: RAGPipeline | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Evaluate a child's immunization status and answer questions using grounded RAG.

    Args:
        child_id_or_data: Child ID string (fetched from DB) or dictionary with 'dob' and 'dose_history'.
        question: Free-text question about the child's immunization.
        current_date: Reference evaluation date.
        history: Optional multi-turn ConversationBuffer or list of turns.
        pipeline: Optional RAGPipeline instance (defaults to global pipeline).
        db_path: Optional SQLite database path.

    Returns:
        Structured response dictionary with answer, status, confidence, sources,
        and computed immunization_status.
    """
    import time
    t0 = time.perf_counter()

    if isinstance(child_id_or_data, str):
        child_id = child_id_or_data
        child_record = get_child(child_id, db_path=db_path)
        if not child_record:
            return {
                "status": "error",
                "error": f"Child with ID {child_id!r} not found in database.",
                "answer": "",
                "sources": [],
                "confidence": 0.0,
                "immunization_status": None,
                "latency_ms": {"retrieval": 0, "llm": 0, "total": 0},
            }
    elif isinstance(child_id_or_data, dict):
        child_id = child_id_or_data.get("id", "custom_child")
        child_record = child_id_or_data
    else:
        return {
            "status": "error",
            "error": f"Invalid child input type: {type(child_id_or_data)}. Expected str or dict.",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "immunization_status": None,
            "latency_ms": {"retrieval": 0, "llm": 0, "total": 0},
        }

    dob = child_record.get("dob")
    dose_history = child_record.get("dose_history", [])

    try:
        imm_status = evaluate_child_immunization(
            dob=dob,
            dose_history=dose_history,
            current_date=current_date,
        )
    except ImmunizationError as e:
        return {
            "status": "error",
            "error": str(e),
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "immunization_status": None,
            "latency_ms": {"retrieval": 0, "llm": 0, "total": 0},
        }

    rag = pipeline if pipeline is not None else get_pipeline()

    # Formulate retrieval query and question prompt
    from ..rag.conversation import contextualize_query
    base_contextual = _build_contextual_query(question, imm_status)
    retrieval_query = contextualize_query(
        base_contextual,
        history=history,
        child_context={"immunization_status": imm_status.to_dict(), "age_display": imm_status.age_display},
    )
    augmented_question = _build_augmented_question_for_rag(question, imm_status)

    # Perform retrieval
    t_ret0 = time.perf_counter()
    chunks = rag.retriever.retrieve(retrieval_query)
    if not chunks:
        chunks = rag.retriever.retrieve(question)
    retrieval_ms = int((time.perf_counter() - t_ret0) * 1000)

    if not chunks:
        from ..rag.prompt import INSUFFICIENT_INFO_ANSWER
        return {
            "status": "insufficient_context",
            "answer": INSUFFICIENT_INFO_ANSWER,
            "sources": [],
            "confidence": 0.0,
            "immunization_status": imm_status.to_dict(),
            "child_id": child_id,
            "age_display": imm_status.age_display,
            "latency_ms": {"retrieval": retrieval_ms, "llm": 0, "total": int((time.perf_counter() - t0) * 1000)},
        }

    # Pass the augmented prompt through the grounded pipeline
    from ..rag.pipeline import retrieval_confidence
    from ..rag.prompt import SYSTEM_PROMPT, build_prompt
    
    t1 = time.perf_counter()
    prompt = build_prompt(augmented_question, chunks, history=history)
    try:
        raw_answer = rag.llm.generate(prompt, system=SYSTEM_PROMPT).strip()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "answer": "",
            "sources": [c.source_dict() for c in chunks],
            "confidence": 0.0,
            "immunization_status": imm_status.to_dict(),
            "child_id": child_id,
            "age_display": imm_status.age_display,
            "latency_ms": {"retrieval": retrieval_ms, "llm": 0, "total": int((time.perf_counter() - t0) * 1000)},
        }

    llm_ms = int((time.perf_counter() - t1) * 1000)

    return {
        "status": "ok",
        "answer": raw_answer,
        "confidence": retrieval_confidence([c.similarity for c in chunks]),
        "sources": [c.source_dict() for c in chunks],
        "immunization_status": imm_status.to_dict(),
        "child_id": child_id,
        "age_display": imm_status.age_display,
        "latency_ms": {"retrieval": retrieval_ms, "llm": llm_ms, "total": int((time.perf_counter() - t0) * 1000)},
    }
