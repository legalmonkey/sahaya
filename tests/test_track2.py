import unittest
import tempfile
from pathlib import Path

from src.database import initialise
from src.track2_repository import Track2Repository

from src.track2 import Track2Service


class RecordingExplainer:
    """Test boundary only: production always receives SahayaPipeline."""
    def __init__(self):
        self.queries = []

    def answer(self, query):
        self.queries.append(query)
        return {"answer": "test explanation", "source_chunks": [{"id": "test-source"}], "confidence": 0.8}


class Track2Tests(unittest.TestCase):
    def setUp(self):
        self.explainer = RecordingExplainer()
        self.service = Track2Service(self.explainer)
        self.mother = {"id": "mother-1", "age": 24, "is_pregnant": True, "is_lactating": False, "trimester": "2"}

    def test_high_risk_record_raises_real_rule_flags(self):
        result = self.service.assess_risk(self.mother, {"bp": "164/112", "hb_level": 6.4, "danger_signs": ["severe headache with blurred vision"]})
        self.assertEqual(result["severity"], "critical")
        self.assertEqual([flag["code"] for flag in result["risk_flags"]], ["severe_anaemia", "severe_hypertension", "danger_sign"])
        self.assertTrue(all(flag["explanation"]["source_chunks"] for flag in result["risk_flags"]))

    def test_unseen_anaemia_and_hypertension_record_is_deterministic(self):
        record = {"bp": "145/92", "hb_level": 9.8, "danger_signs": []}
        first = self.service.assess_risk(self.mother, record)
        second = self.service.assess_risk(self.mother, record)
        self.assertEqual([(item["code"], item["severity"]) for item in first["risk_flags"]], [(item["code"], item["severity"]) for item in second["risk_flags"]])

    def test_pmmvy_and_pmsma_qualify_from_facts_not_precomputed_answers(self):
        household = {"id": "h1", "category": "SC", "annual_income_inr": 950000, "is_pmjay_listed": False}
        results = self.service.assess_eligibility(household, self.mother, [{"dob": "2023-01-01"}])["scheme_matches"]
        by_name = {item["scheme_name"]: item["eligible"] for item in results}
        self.assertTrue(by_name["PMMVY"])
        self.assertTrue(by_name["PMSMA"])
        self.assertFalse(by_name["Ayushman Bharat PM-JAY"])
        self.assertTrue(by_name["RBSK"])

    def test_non_qualifying_pmmvy_record_is_deterministic(self):
        mother = {"id": "mother-2", "age": 25, "is_pregnant": True, "is_lactating": False, "trimester": "1"}
        household = {"id": "h2", "category": "GENERAL", "annual_income_inr": 900000, "is_pmjay_listed": False}
        first = self.service.assess_eligibility(household, mother, [])
        second = self.service.assess_eligibility(household, mother, [])
        self.assertFalse(next(item for item in first["scheme_matches"] if item["scheme_name"] == "PMMVY")["eligible"])
        self.assertEqual([item["eligible"] for item in first["scheme_matches"]], [item["eligible"] for item in second["scheme_matches"]])

    def test_integration_computes_then_persists_track2_outputs(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            database = Path(temp) / "sahaya.db"
            root = Path(__file__).parents[1]
            initialise(database, root / "db" / "migrations" / "001_shared_schema.sql", (
                root / "db" / "migrations" / "002_track2_facts.sql", root / "db" / "migrations" / "003_track2_mother_facts.sql"))
            repository = Track2Repository(database, self.service)
            repository.seed_demo_inputs()
            result = repository.evaluate_and_persist("demo-hh-001")
            self.assertTrue(result["risk"]["risk_flags"])
            stored = repository.household_view("demo-hh-001")
            self.assertIn("risk_flags_json", stored["mother"])
            self.assertNotEqual(stored["mother"]["risk_flags_json"], "[]")


if __name__ == "__main__":
    unittest.main()
