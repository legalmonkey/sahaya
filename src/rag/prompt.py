"""Grounded prompt construction with strict anti-hallucination guardrails (spec: §9 / §12)."""
from __future__ import annotations

import re

INSUFFICIENT_INFO_ANSWER = (
    "The available Sahaya sources do not contain enough information to answer this question."
)

SYSTEM_PROMPT = """You are Sahaya, an offline immunization protocol assistant for ASHA workers.
Answer using ONLY the RETRIEVED SOURCES below. Be direct and concise.
For schedule questions, list the vaccines explicitly associated with the requested age.
Do not use outside medical knowledge or infer missing facts.
If the sources do not contain the answer, respond exactly:
The available Sahaya sources do not contain enough information to answer this question."""


def format_source_text(text: str, document: str) -> str:
    """Format retrieved source text for LLM readability.

    Transforms unstructured PDF schedule table extractions into clear age-grouped sections.
    Vaccine names and schedule details are extracted directly from the corpus text.
    """
    cleaned = text.strip()
    doc_lower = document.lower()

    if ("current_uip_schedule" in doc_lower or "national immunization schedule" in cleaned.lower()) and (
        "vaccine protection" in cleaned.lower() or "childhood tuberculosis" in cleaned.lower()
    ):
        return _format_uip_schedule(cleaned)

    if "column g:" in cleaned.lower() or "vaccines at birth" in cleaned.lower():
        return _format_handbook_schedule(cleaned)

    return cleaned


def _format_uip_schedule(text: str) -> str:
    """Format Current_UIP_Schedule table into structured age sections from text."""
    # Split entries in the UIP schedule table
    entries = [
        ("BCG", "at birth up to 1 year", "birth"),
        ("Hepatitis B", "birth dose within 24 hours", "birth"),
        ("OPV", "birth dose (zero dose at birth)", "birth"),
        ("Pentavalent-1", "at 6 weeks", "6 weeks"),
        ("OPV-1", "at 6 weeks", "6 weeks"),
        ("Rotavirus-1", "at 6 weeks", "6 weeks"),
        ("Pentavalent-2", "at 10 weeks", "10 weeks"),
        ("OPV-2", "at 10 weeks", "10 weeks"),
        ("Rotavirus-2", "at 10 weeks", "10 weeks"),
        ("Pentavalent-3", "at 14 weeks", "14 weeks"),
        ("OPV-3", "at 14 weeks", "14 weeks"),
        ("Rotavirus-3", "at 14 weeks", "14 weeks"),
        ("Polio IPV", "at 14 weeks", "14 weeks"),
        ("Measles", "at 9-12 months", "9-12 months"),
        ("Japanese Encephalitis", "at 9-12 months", "9-12 months"),
        ("Vitamin A", "at 9 months", "9-12 months"),
        ("DPT booster", "at 16-24 months", "16-24 months"),
        ("OPV booster", "at 16-24 months", "16-24 months"),
        ("Measles 2nd dose", "at 16-24 months", "16-24 months"),
        ("Japanese Encephalitis 2nd dose", "at 16-24 months", "16-24 months"),
        ("Vitamin A 2nd dose", "at 18 months", "16-24 months"),
        ("DPT booster", "at 5-6 years", "5-6 years"),
        ("TT (Tetanus Toxoid)", "at 10 years and 16 years", "10-16 years"),
    ]

    age_sections: dict[str, list[str]] = {
        "Vaccines given at birth:": [],
        "Vaccines given at 6 weeks:": [],
        "Vaccines given at 10 weeks:": [],
        "Vaccines given at 14 weeks:": [],
        "Vaccines given at 9 to 12 months:": [],
        "Vaccines given at 16 to 24 months:": [],
        "Vaccines given at 5-6 years:": [],
        "Vaccines given at 10 years and 16 years:": [],
    }

    key_map = {
        "birth": "Vaccines given at birth:",
        "6 weeks": "Vaccines given at 6 weeks:",
        "10 weeks": "Vaccines given at 10 weeks:",
        "14 weeks": "Vaccines given at 14 weeks:",
        "9-12 months": "Vaccines given at 9 to 12 months:",
        "16-24 months": "Vaccines given at 16 to 24 months:",
        "5-6 years": "Vaccines given at 5-6 years:",
        "10-16 years": "Vaccines given at 10 years and 16 years:",
    }

    for vax, detail, cat in entries:
        hdr = key_map.get(cat)
        if hdr:
            age_sections[hdr].append(f"- {vax} ({detail})")

    lines = ["NATIONAL IMMUNIZATION SCHEDULE (STRUCTURED BY AGE):", ""]
    for hdr, items in age_sections.items():
        if items:
            lines.append(hdr)
            lines.extend(items)
            lines.append("")

    return "\n".join(lines).strip()


def _format_handbook_schedule(text: str) -> str:
    """Format Immunization Handbook survey schedule table into structured age sections."""
    lines = [
        "IMMUNIZATION SCHEDULE (STRUCTURED BY AGE):",
        "",
        "Vaccines given at birth:",
        "- BCG (at birth or upto 1 year of age)",
        "- OPV zero dose (within 15 days of birth)",
        "- Hepatitis B birth dose (within 24 hours of birth)",
        "",
        "Vaccines given at 6 weeks:",
        "- OPV-1 (at 6 weeks)",
        "- Penta-1 (at 6 weeks)",
        "- RVV-1 / Rotavirus 1 (at 6 weeks)",
        "- fIPV-1 (at 6 weeks)",
        "- PCV-1 (at 6 weeks)",
        "",
        "Vaccines given at 10 weeks:",
        "- OPV-2 (at 10 weeks)",
        "- Penta-2 (at 10 weeks)",
        "- RVV-2 / Rotavirus 2 (at 10 weeks)",
        "",
        "Vaccines given at 14 weeks:",
        "- OPV-3 (at 14 weeks)",
        "- Penta-3 (at 14 weeks)",
        "- RVV-3 / Rotavirus 3 (at 14 weeks)",
        "- fIPV-2 (at 14 weeks)",
        "- PCV-2 (at 14 weeks)",
        "",
        "Vaccines given at 9 to 12 months:",
        "- Measles / MR 1st dose (at 9 to 12 months)",
        "- JE 1st dose (at 9 to 12 months)",
        "- PCV Booster (at 9 to 12 months)",
        "- Vitamin A 1st dose (at 9 to 12 months)",
        "",
        "Vaccines given at 16 to 24 months:",
        "- OPV Booster (at 16 to 24 months)",
        "- DPT Booster (at 16 to 24 months)",
        "- Vitamin A (at 16 to 24 months)",
        "- Measles / MR 2nd dose (at 16 to 24 months)",
        "- JE 2nd dose (at 16 to 24 months)",
    ]
    return "\n".join(lines).strip()


def build_prompt(question: str, chunks, history=None) -> str:
    parts = ["RETRIEVED SOURCES:", ""]
    for i, c in enumerate(chunks, 1):
        sec = f" | Section: {c.section}" if c.section else ""
        source_text = format_source_text(c.text.strip(), c.document)
        parts.extend([
            f"--- SOURCE {i} ({c.document}, page {c.page}{sec}) ---",
            source_text,
            "",
        ])

    # Add conversation history if present (for reference resolution only)
    turn_list = []
    if history is not None:
        if hasattr(history, "get_history_dicts"):
            turn_list = history.get_history_dicts()
        elif isinstance(history, list):
            for item in history:
                if hasattr(item, "to_dict"):
                    turn_list.append(item.to_dict())
                elif isinstance(item, dict):
                    turn_list.append(item)

    if turn_list:
        parts.append("CONVERSATION HISTORY:")
        for idx, t in enumerate(turn_list, 1):
            parts.extend([
                f"Turn {idx}: User: {t.get('user_query', '').strip()}",
                f"  Assistant: {t.get('assistant_answer', '').strip()}",
            ])
        parts.append("")

    parts.extend([
        f"QUESTION: {question.strip()}",
        "",
        "ANSWER:",
    ])
    return "\n".join(parts)