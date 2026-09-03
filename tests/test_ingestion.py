"""Unit tests for pdf_loader + chunker (no Ollama, no embedding model needed)."""
from src.ingestion.chunker import chunk_document
from src.ingestion.pdf_loader import PageText, clean_text, discover_pdfs


def page(text: str, p: int = 1, doc: str = "t.pdf") -> PageText:
    return PageText(doc, p, text, None)


def para(words: int, seed: int = 0) -> str:
    return " ".join(f"w{seed}_{i}" for i in range(words)) + "."


# ---------------- clean_text ----------------

def test_clean_text_rejoins_hyphenated_words():
    assert clean_text("immu-\nnization") == "immunization"

def test_clean_text_collapses_blank_runs():
    assert clean_text("a\n\n\n\n\nb") == "a\n\nb"

def test_discover_pdfs_recursive(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.pdf").write_bytes(b"x")
    (tmp_path / "sub" / "b.PDF").write_bytes(b"x")
    (tmp_path / "c.txt").write_text("no")
    found = discover_pdfs(tmp_path)
    assert [p.name for p in found] == ["a.pdf", "b.PDF"]


# ---------------- chunker ----------------

def test_chunks_respect_word_budget_and_cover_content():
    text = "\n\n".join(para(120, i) for i in range(10))
    chunks = chunk_document([page(text)], "t.pdf", max_words=300, min_words=100,
                            overlap_sentences=1)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c["text"].split()) <= 300 + 40          # max + small overlap slack
    blob = " ".join(c["text"] for c in chunks)
    for i in range(10):
        assert f"w{i}_0" in blob                            # nothing lost

def test_page_metadata_preserved():
    chunks = chunk_document(
        [page(para(120), 1), page(para(120), 2), page(para(120), 3)], "t.pdf",
        max_words=250, min_words=50, overlap_sentences=0)
    pages = [c["metadata"]["page"] for c in chunks]
    assert pages == sorted(pages) and 1 in pages and 3 in pages
    assert all(c["metadata"]["document"] == "t.pdf" for c in chunks)

def test_section_detected_from_numbered_heading():
    text = "3.2 Cold Chain Equipment\n\n" + para(150)
    chunks = chunk_document([page(text)], "t.pdf", max_words=600,
                            min_words=50, overlap_sentences=0)
    assert chunks[0]["metadata"]["section"] == "3.2 Cold Chain Equipment"

def test_section_is_null_when_unknown():
    chunks = chunk_document([page(para(150))], "t.pdf", max_words=600,
                            min_words=50, overlap_sentences=0)
    assert chunks[0]["metadata"]["section"] == ""           # "" == null in storage

def test_bullet_block_is_never_split():
    bullets = "\n".join(f"• vaccine {i} given at week {i} " + f"detail{i} " * 25
                        for i in range(8))
    text = para(120) + "\n\n" + bullets + "\n\n" + para(120)
    chunks = chunk_document([page(text)], "t.pdf", max_words=200, min_words=50,
                            overlap_sentences=0)
    # some single chunk must contain the whole bullet block intact
    assert any(("• vaccine 0" in c["text"] and "• vaccine 7" in c["text"]) for c in chunks)

def test_overlap_between_consecutive_chunks():
    sentences = [f"Sentence {i} details key immunization facts." for i in range(30)]
    text = " ".join(sentences)
    chunks = chunk_document([page(text)], "t.pdf", max_words=50, min_words=20,
                            overlap_sentences=2)
    assert len(chunks) >= 2
    # Ensure consecutive chunks share overlap sentences
    overlap_found = False
    for s in chunks[0]["text"].split("."):
        s_clean = s.strip()
        if len(s_clean) > 10 and s_clean in chunks[1]["text"]:
            overlap_found = True
            break
    assert overlap_found