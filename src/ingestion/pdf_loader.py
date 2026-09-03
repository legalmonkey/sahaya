"""PDF discovery + text extraction with per-page provenance (spec: §6)."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

log = logging.getLogger("sahaya.ingest")


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be opened or yields (almost) no text."""


@dataclass
class PageText:
    document: str
    page: int          # 1-based
    text: str
    error: str | None = None


def discover_pdfs(folder: Path) -> list[Path]:
    """Find every PDF under `folder` (recursive). No filenames are hardcoded."""
    if not folder.exists():
        return []
    return sorted({p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"})


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTI_SPACE = re.compile(r"[ \t]{3,}")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # rejoin hyphen-split words
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _MULTI_SPACE.sub(" ", text)              # table alignment isn't meaningful to embedders
    return text.strip("\n")


def extract_pages(path: Path) -> list[PageText]:
    """Extract cleaned text per page.

    Whole-file failures raise PdfExtractionError (with the filename).
    Individual page failures are logged and returned with `error` set — provenance is never lost.
    """
    name = path.name
    try:
        reader = PdfReader(str(path))
    except Exception as e:  # noqa: BLE001
        raise PdfExtractionError(f"{name}: cannot open PDF ({e})") from e

    pages: list[PageText] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as e:  # noqa: BLE001
            log.warning("%s page %d: extraction failed (%s)", name, i, e)
            pages.append(PageText(name, i, "", f"page {i}: {e}"))
            continue
        pages.append(PageText(name, i, clean_text(raw), None))

    if sum(len(p.text) for p in pages) < 50:
        raise PdfExtractionError(
            f"{name}: almost no extractable text — the PDF is probably scanned images. "
            f"Day 1 has no OCR; re-export a text PDF or OCR it first."
        )
    return pages