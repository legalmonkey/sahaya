"""Grounded prompt construction with strict anti-hallucination guardrails (spec: §9 / §12)."""
from __future__ import annotations

INSUFFICIENT_INFO_ANSWER = (
    "The available Sahaya sources do not contain enough information to answer this question."
)

SYSTEM_PROMPT = """You are Sahaya, an offline protocol assistant for ASHA workers.

You MUST answer using ONLY the retrieved context supplied in this prompt.

The retrieved context is the only authoritative knowledge available to you.

Do NOT use:
- your pretrained/general knowledge
- WHO knowledge unless WHO content is explicitly present in the retrieved context
- CDC knowledge unless CDC content is explicitly present in the retrieved context
- information from the internet
- assumptions
- common medical knowledge

Every factual medical/protocol claim in your answer must be supported by the retrieved context.

Do not introduce facts, numbers, thresholds, vaccine recommendations, contraindications, timing rules, or medical advice that are not supported by the retrieved context.

If the retrieved context does not contain enough information to answer the question safely and accurately, say:
"The available Sahaya sources do not contain enough information to answer this question."

Do NOT fill the missing information from your own knowledge.
Use only the supplied context."""


def build_prompt(question: str, chunks) -> str:
    parts = [
        "RETRIEVED SOURCES:",
        "",
    ]
    for i, c in enumerate(chunks, 1):
        sec = f" | Section: {c.section}" if c.section else ""
        parts.extend([
            f"SOURCE {i}",
            f"Document: {c.document}",
            f"Page: {c.page}{sec}",
            "Content:",
            c.text.strip(),
            "",
        ])

    parts.extend([
        "----------------------------------------",
        f"USER QUESTION: {question.strip()}",
        "",
        "INSTRUCTIONS:",
        "1. Answer the USER QUESTION using ONLY the facts directly provided in the RETRIEVED SOURCES above.",
        "2. If the retrieved sources do not contain enough information to answer the question safely and accurately, output exactly:",
        f'"{INSUFFICIENT_INFO_ANSWER}"',
        "3. Do NOT use outside knowledge, unmentioned medical guidelines, or external organizations (such as WHO, CDC) unless they appear explicitly in the retrieved sources above.",
        "4. Be direct, concise, and grounded.",
        "",
        "ANSWER:",
    ])
    return "\n".join(parts)