import unittest
from pathlib import Path
import sqlite3

from src.database import initialise
from src.retrieval import LocalTfidfRetriever


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = LocalTfidfRetriever(Path(__file__).parents[1] / "data" / "corpus.json")

    def test_retrieves_opv_schedule(self):
        self.assertEqual(self.retriever.search("When are oral polio vaccine doses due?")[0].chunk["id"], "mohfw-nis-opv-002")

    def test_retrieves_hepatitis_birth_dose(self):
        self.assertEqual(self.retriever.search("How soon after an institutional delivery is hepatitis B given?")[0].chunk["id"], "mohfw-nis-hepb-003")

    def test_retrieves_pmsma_fixed_day(self):
        self.assertEqual(self.retriever.search("On which day does PMSMA provide antenatal care?")[0].chunk["id"], "nhm-pmsma-anc-002")

    def test_confidence_is_derived(self):
        strong = self.retriever.confidence(self.retriever.search("OPV polio booster 16 24 months"))
        weak = self.retriever.confidence(self.retriever.search("unrelated agricultural rainfall forecast"))
        self.assertGreater(strong, weak)

    def test_multi_turn_followup_retrieval(self):
        # When follow-up is ambiguous, folding prior query resolves correctly
        prior_query = "When are oral polio vaccine doses due?"
        followup = "what about the booster dose then?"
        folded = prior_query + " " + followup
        results = self.retriever.search(folded)
        self.assertEqual(results[0].chunk["id"], "mohfw-nis-opv-002")

    def test_shared_schema_creates_required_tables(self):
        migration = (Path(__file__).parents[1] / "db" / "migrations" / "001_shared_schema.sql").read_text(encoding="utf-8")
        with sqlite3.connect(":memory:") as connection:
            connection.executescript(migration)
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"households", "mothers", "children", "anc_checkups", "scheme_matches", "priority_queue"}.issubset(tables))


if __name__ == "__main__":
    unittest.main()
