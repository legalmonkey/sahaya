"""Lightweight multi-turn conversation buffer and query contextualization (spec: Part A Task 1).

Maintains a bounded 1–2 turn history buffer, resolves pronoun and follow-up references
for RAG retrieval, while preserving strict corpus grounding and refusal guardrails.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..config import SETTINGS

_FOLLOWUP_INDICATORS = {
    "it", "its", "this", "that", "these", "those", "they", "them",
    "second", "2nd", "third", "3rd", "first", "1st", "fourth", "4th", "booster",
    "dose", "doses", "route", "site", "contraindication", "contraindications",
    "side", "effect", "effects", "adverse", "age", "interval", "schedule",
    "what about", "how about", "and", "why", "when", "how", "next", "missed",
    "delay", "delayed", "overdue", "due", "repeat", "given", "give",
}

_STOP_WORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the to was "
    "were will with what when where which who whom this these those not no do does did "
    "can could should would may might must shall your you their our if then than so such "
    "tell me about what is the please explain".split()
)


@dataclass
class Turn:
    user_query: str
    assistant_answer: str
    sources: list[dict] = field(default_factory=list)
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_query": self.user_query,
            "assistant_answer": self.assistant_answer,
            "sources": self.sources,
            "context": self.context,
        }


class ConversationBuffer:
    """Bounded multi-turn memory buffer holding the most recent turns."""

    def __init__(self, max_turns: int | None = None) -> None:
        self.max_turns = max_turns if max_turns is not None else SETTINGS.conversation_max_turns
        self.turns: list[Turn] = []

    def add_turn(
        self,
        user_query: str,
        assistant_answer: str,
        sources: list[dict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        turn = Turn(
            user_query=user_query.strip(),
            assistant_answer=assistant_answer.strip(),
            sources=sources or [],
            context=context,
        )
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_history(self) -> list[Turn]:
        return list(self.turns)

    def get_history_dicts(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.turns]

    def clear(self) -> None:
        self.turns.clear()

    def reset(self) -> None:
        self.clear()

    def is_empty(self) -> bool:
        return len(self.turns) == 0

    def __len__(self) -> int:
        return len(self.turns)


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    return [t for t in tokens if t.lower() not in _STOP_WORDS and len(t) > 1]


def contextualize_query(
    query: str,
    history: ConversationBuffer | list[Turn] | list[dict[str, Any]] | None = None,
    child_context: dict[str, Any] | None = None,
) -> str:
    """Fold conversation history into a retrieval-friendly query without overriding RAG.

    Args:
        query: Current user question.
        history: ConversationBuffer, list of Turn objects, or list of turn dicts.
        child_context: Optional child status or metadata.

    Returns:
        A search query that includes referenced prior topic terms for retrieval.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        return ""

    # Normalize history to list of dicts/turns
    turn_list: list[dict[str, Any]] = []
    if isinstance(history, ConversationBuffer):
        turn_list = history.get_history_dicts()
    elif isinstance(history, list):
        for item in history:
            if isinstance(item, Turn):
                turn_list.append(item.to_dict())
            elif isinstance(item, dict):
                turn_list.append(item)

    if not turn_list and not child_context:
        return clean_q

    # Collect previous context keywords
    context_keywords: list[str] = []
    for turn in turn_list:
        prev_q = turn.get("user_query", "")
        # Extract meaningful subject keywords from previous turn question
        kw = _extract_keywords(prev_q)
        for k in kw:
            if k.lower() not in [x.lower() for x in context_keywords]:
                context_keywords.append(k)

    # If child context exists, extract due/overdue vaccine mentions
    if child_context:
        imm = child_context.get("immunization_status", child_context)
        if isinstance(imm, dict):
            due = [d.get("vaccine_name", "") for d in imm.get("due", []) if d.get("vaccine_name")]
            overdue = [d.get("vaccine_name", "") for d in imm.get("overdue", []) if d.get("vaccine_name")]
            all_vax = due + overdue
            for v in all_vax:
                if v and v.lower() not in [x.lower() for x in context_keywords]:
                    context_keywords.append(v)

    if not context_keywords:
        return clean_q

    # Detect if current query refers to previous context (pronouns, dose numbers, short follow-ups)
    q_words = set(re.findall(r"[A-Za-z0-9]+", clean_q.lower()))
    is_followup = (
        len(q_words) <= 6
        or bool(q_words & _FOLLOWUP_INDICATORS)
        or not any(kw.lower() in clean_q.lower() for kw in context_keywords)
    )

    if is_followup:
        # Append context topic terms to help retrieval pinpoint the right chunks
        topic_str = " ".join(context_keywords[:5])
        return f"{clean_q} ({topic_str})"

    return clean_q
