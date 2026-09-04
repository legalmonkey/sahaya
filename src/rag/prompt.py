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


def build_prompt(question: str, chunks, history=None) -> str:
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

    parts.append("----------------------------------------")

    # Add conversation history if present
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
        parts.extend([
            "CONVERSATION HISTORY (FOR CONTEXT / REFERENCE RESOLUTION ONLY):",
            "",
        ])
        for idx, t in enumerate(turn_list, 1):
            parts.extend([
                f"Turn {idx}:",
                f"User: {t.get('user_query', '').strip()}",
                f"Assistant: {t.get('assistant_answer', '').strip()}",
                "",
            ])
        parts.append("----------------------------------------")

    parts.extend([
        f"USER QUESTION: {question.strip()}",
        "",
        "INSTRUCTIONS:",
        "1. Answer the USER QUESTION using ONLY the facts directly provided in the RETRIEVED SOURCES above.",
        "2. If conversation history is provided, you may use it solely to understand pronouns, dose references, or follow-ups in the USER QUESTION. You must NEVER use conversation history as medical or factual evidence; all facts in your answer must be directly supported by RETRIEVED SOURCES.",
        "3. If the retrieved sources do not contain enough information to answer the question safely and accurately, output exactly:",
        f'"{INSUFFICIENT_INFO_ANSWER}"',
        "4. Do NOT use outside knowledge, unmentioned medical guidelines, or external organizations (such as WHO, CDC) unless they appear explicitly in the retrieved sources above.",
        "5. Be direct, concise, and grounded.",
        "",
        "ANSWER:",
    ])
    return "\n".join(parts)