"""Build retrievable local chunks from official PDFs already bundled in the repo.

Run only when source PDFs change. The app never downloads at runtime.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data"
SOURCES = DATA / "official_sources"
OUT = DATA / "corpus.pdf_chunks.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunks(text: str, size: int = 1200, overlap: int = 180):
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + size)
        if end < len(text):
            boundary = text.rfind(". ", cursor, end)
            if boundary > cursor + 400:
                end = boundary + 1
        yield text[cursor:end]
        if end >= len(text):
            break
        cursor = max(end - overlap, cursor + 1)


def main() -> None:
    manifest = json.loads((SOURCES / "manifest.json").read_text(encoding="utf-8"))
    output = []
    for source in manifest:
        if not source.get("index", True):
            print(f"Kept source PDF but skipped text extraction: {source['file']}")
            continue
        reader = PdfReader(SOURCES / source["file"])
        selected_pages = set(source.get("pages", range(1, len(reader.pages) + 1)))
        for page_number, page in enumerate(reader.pages, start=1):
            if page_number not in selected_pages:
                continue
            try:
                text = normalize(page.extract_text() or "")
            except Exception as exc:
                # Some government PDFs contain a damaged compressed page stream.
                # Keep every readable page; do not make the offline build fail.
                print(f"Skipped unreadable {source['file']} page {page_number}: {exc}")
                continue
            if len(text) < 100:
                continue
            for index, chunk in enumerate(chunks(text), start=1):
                output.append({
                    "id": f"pdf-{Path(source['file']).stem}-p{page_number}-{index}",
                    "title": source["title"], "authority": source["authority"],
                    "source_url": source["url"], "source_label": f"Bundled PDF, page {page_number}",
                    "retrieved_on": "2026-09-04", "text": chunk,
                })
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(output)} offline PDF chunks to {OUT}")


if __name__ == "__main__":
    main()
