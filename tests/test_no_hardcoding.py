"""Spec §15 / acceptance H: prove no question-specific answers are baked into the code.
Scans all source files for every test question string — none may appear."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

try:
    from tests.questions import KNOWN_QUESTIONS, UNSEEN_QUESTIONS
except ImportError:
    from questions import KNOWN_QUESTIONS, UNSEEN_QUESTIONS

SRC = (list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py"))
       + [ROOT / "main.py"])


def test_no_question_strings_in_code():
    blob = "\n".join(p.read_text(encoding="utf-8") for p in SRC if p.exists()).lower()
    for q in KNOWN_QUESTIONS + UNSEEN_QUESTIONS:
        assert q.lower() not in blob, f"question found hardcoded in source: {q!r}"