"""Paragraph/section-aware chunker (spec: §7).

Strategy
- Rebuild paragraphs from PDF lines: soft-wrapped lines joined, bullet runs kept as ONE
  block (so schedules/tables/lists are never split mid-block — paragraphs are atomic
  packing units).
- Track the current section heading while streaming (conservative heuristics; when in
  doubt the section is None — we never invent metadata).
- Pack whole paragraphs greedily up to CHUNK_MAX_WORDS; the last N sentences of a chunk
  are repeated at the start of the next (overlap).
- An oversized single paragraph is split on sentence boundaries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_loader import PageText

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TERMINAL = re.compile(r"[.!?:;]$")
_BULLET = re.compile(r"^(?:[•▪●○·‣–—-]|\(?\d{1,2}[.)]|\(?[a-zA-Z][.)])\s+")
_NUM_PREFIX = re.compile(r"^(?P<num>\d+(?:\.\d+){0,3})\s+(?P<rest>.+)$")
_ALPHA_TITLE = re.compile(r"^[A-Za-z][A-Za-z ,&/()\-'’]+$")
_SECTION_KEYWORDS = ("chapter", "annex", "appendix", "section", "part", "table", "box", "figure")


def _looks_like_heading(line: str) -> bool:
    """Best-effort heading detection. Deliberately conservative (false negatives are
    fine — section stays null; false positives are minimized)."""
    s = line.strip()
    words = s.split()
    if not (4 <= len(s) <= 90) or not (2 <= len(words) <= 12):
        return False
    if s.endswith((".", ",", ";")):
        return False
    m = _NUM_PREFIX.match(s)                       # "3.2 Cold Chain Equipment"
    if m and _ALPHA_TITLE.match(m.group("rest").strip()) and len(m.group("rest").split()) >= 2:
        return True
    if s.lower().startswith(_SECTION_KEYWORDS):    # "Chapter 4", "Table 5.1 ..."
        return True
    if s == s.upper() and re.search(r"[A-Z]{3}", s):   # short ALL-CAPS line
        return True
    return False


@dataclass
class _Para:
    page: int
    section: str | None
    text: str
    is_list: bool


def _keep_paragraph(text: str) -> bool:
    """Drop folios, page numbers and other tiny artifacts."""
    return len(text) >= 12 and len(text.split()) >= 3


def _paragraphs_from_page(page_text: str, page: int, section: str | None):
    paras: list[_Para] = []
    buf: list[str] = []
    buf_is_list = False

    def close() -> None:
        nonlocal buf
        if not buf:
            return
        sep = "\n" if buf_is_list else " "
        text = sep.join(x.strip() for x in buf).strip()
        if _keep_paragraph(text):
            paras.append(_Para(page, section, text, buf_is_list))
        buf = []

    for raw_line in page_text.split("\n"):
        line = raw_line.strip()
        if not line:
            close()
            continue
        if _looks_like_heading(line):
            close()
            section = line
            continue
        is_bullet = bool(_BULLET.match(line))
        if buf:
            if is_bullet != buf_is_list:
                close()
            elif not buf_is_list and _TERMINAL.search(buf[-1]):
                close()                             # sentence finished → new paragraph
        if not buf:
            buf_is_list = is_bullet
        buf.append(line)
    close()
    return paras, section


def _split_sentences_fit(text: str, max_words: int) -> list[str]:
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    pieces, cur, cur_w = [], [], 0
    for s in sentences:
        w = len(s.split())
        if cur and cur_w + w > max_words:
            pieces.append(" ".join(cur))
            cur, cur_w = [], 0
        cur.append(s)
        cur_w += w
    if cur:
        pieces.append(" ".join(cur))
    return [p for p in pieces if p.strip()]


def _tail_sentences(group: list[_Para], n: int) -> list[_Para]:
    """Overlap seed: last n sentences of the chunk, carrying their own page/section."""
    if n <= 0 or not group:
        return []
    last = group[-1]
    sentences = [s.strip() for s in _SENT_SPLIT.split(last.text) if s.strip()]
    if len(sentences) <= 1:
        return []
    tail = " ".join(sentences[-n:])
    if tail == last.text:
        return []
    return [_Para(last.page, last.section, tail, last.is_list)]


def chunk_document(
    pages: list[PageText],
    document: str,
    *,
    max_words: int = 600,
    min_words: int = 250,
    overlap_sentences: int = 2,
) -> list[dict]:
    paragraphs: list[_Para] = []
    section: str | None = None
    for p in pages:
        page_paras, section = _paragraphs_from_page(p.text, p.page, section)
        paragraphs.extend(page_paras)

    # 1) greedy packing of whole paragraphs
    packed: list[list[_Para]] = []
    cur: list[_Para] = []
    cur_words = 0
    for para in paragraphs:
        w = len(para.text.split())
        if w > max_words:                                    # oversized single paragraph
            if cur:
                packed.append(cur)
                cur, cur_words = [], 0
            for piece in _split_sentences_fit(para.text, max_words):
                packed.append([_Para(para.page, para.section, piece, para.is_list)])
            continue
        if cur and cur_words + w > max_words:
            packed.append(cur)
            cur, cur_words = [], 0
        cur.append(para)
        cur_words += w
    if cur:
        packed.append(cur)

    # 2) merge a tiny final chunk into its neighbour
    if len(packed) >= 2:
        last_w = sum(len(p.text.split()) for p in packed[-1])
        prev_w = sum(len(p.text.split()) for p in packed[-2])
        if last_w < min_words // 2 and prev_w + last_w <= max_words + 100:
            packed[-2] = packed[-2] + packed[-1]
            packed.pop()

    # 3) prepend overlap tail from previous chunk
    groups: list[list[_Para]] = []
    prev_tail: list[_Para] = []
    for group in packed:
        group = prev_tail + group
        prev_tail = _tail_sentences(group, overlap_sentences)
        groups.append(group)

    # 4) materialize
    out: list[dict] = []
    for i, group in enumerate(groups):
        text = "\n\n".join(p.text for p in group).strip()
        if not text:
            continue
        section_i = next((p.section for p in group if p.section is not None), None)
        out.append({
            "chunk_id": f"{document}::p{group[0].page}::c{i:04d}",
            "text": text,
            "metadata": {
                "document": document,
                "page": group[0].page,          # page of first paragraph
                "page_end": group[-1].page,
                "section": section_i or "",     # Chroma metadata cannot be null → "" means null
                "chunk_seq": i,
            },
        })
    return out