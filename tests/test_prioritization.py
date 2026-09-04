"""Unit tests for the deterministic PrioritizationEngine (Track C).
Validates that scoring, tiering, reasons generation, and ranking behave strictly
according to clinical and visit rules, with zero hardcoding.
"""
from __future__ import annotations

import json
import sqlite3
import unittest
from datetime import date
from pathlib import Path

from src.database import initialise
from src.prioritization import PrioritizationEngine


class PrioritizationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        migration = Path(__file__).resolve().parent.parent / "db" / "migrations" / "001_shared_schema.sql"
        self.db.executescript(migration.read_text(encoding="utf-8"))
        self.engine = PrioritizationEngine()
        self.ref_date = date(2026, 9, 3)

    def tearDown(self):
        self.db.close()

    def test_empty_database_returns_empty_results(self):
        results = self.engine.refresh_priority_queue(self.db, reference_date=self.ref_date)
        self.assertEqual(results, [])
        retrieved = self.engine.get_prioritized_households(self.db)
        self.assertEqual(retrieved, [])

    def test_routine_household_has_low_urgency(self):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO households (id, name, village) VALUES ('hh-01', 'Sunita Devi', 'Rampur')"
        )
        cursor.execute(
            "INSERT INTO mothers (id, household_id, last_visit_date) VALUES ('m-01', 'hh-01', '2026-08-25')"
        )
        # Child with completed BCG and upcoming dose beyond 7 days
        doses = [
            {"vaccine": "BCG", "date_given": "2026-01-10", "due_date": "2026-01-01"},
            {"vaccine": "OPV-1", "date_given": "2026-02-15", "due_date": "2026-02-15"},
            {"vaccine": "OPV-2", "date_given": None, "due_date": "2026-10-15"},
        ]
        cursor.execute(
            "INSERT INTO children (id, household_id, dob, dose_history_json) VALUES ('c-01', 'hh-01', '2026-01-01', ?)",
            (json.dumps(doses),)
        )
        self.db.commit()

        result = self.engine.evaluate_household("hh-01", self.db, reference_date=self.ref_date)
        self.assertIsNotNone(result)
        self.assertEqual(result.urgency_tier, "LOW")
        self.assertLess(result.score, 30.0)
        self.assertTrue(any("पूर्ण" in r or "Routine" in r for r in result.reasons))

    def test_overdue_vaccine_triggers_score_and_reason(self):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO households (id, name, village) VALUES ('hh-02', 'Radha Sharma', 'Rampur')"
        )
        # Dose overdue by 20 days
        doses = [
            {"vaccine": "Penta-3", "date_given": None, "due_date": "2026-08-14"},
        ]
        cursor.execute(
            "INSERT INTO children (id, household_id, dob, dose_history_json) VALUES ('c-02', 'hh-02', '2026-04-01', ?)",
            (json.dumps(doses),)
        )
        self.db.commit()

        result = self.engine.evaluate_household("hh-02", self.db, reference_date=self.ref_date)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.score, 35.0)
        self.assertTrue(any("Penta-3" in r and "विलंबित" in r for r in result.reasons))

    def test_maternal_high_bp_and_severe_anemia_triggers_high_urgency(self):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO households (id, name, village) VALUES ('hh-03', 'Meena Devi', 'Rampur')"
        )
        cursor.execute(
            "INSERT INTO mothers (id, household_id, lmp_date, anc_visit_count, last_visit_date) VALUES ('m-03', 'hh-03', '2026-01-01', 1, '2026-08-01')"
        )
        # Checkup with severe high BP (145/95) and severe anemia (Hb 6.4)
        cursor.execute(
            """
            INSERT INTO anc_checkups (id, mother_id, date, bp, hb_level, danger_signs_json)
            VALUES ('anc-01', 'm-03', '2026-08-01', '145/95', 6.4, '["धुंधला दिखना"]')
            """
        )
        self.db.commit()

        result = self.engine.evaluate_household("hh-03", self.db, reference_date=self.ref_date)
        self.assertIsNotNone(result)
        self.assertEqual(result.urgency_tier, "HIGH")
        self.assertGreaterEqual(result.score, 60.0)
        # Check reasons include BP, anemia, and danger signs
        reasons_combined = " ".join(result.reasons)
        self.assertIn("145/95", reasons_combined)
        self.assertIn("गंभीर एनीमिया", reasons_combined)
        self.assertIn("धुंधला दिखना", reasons_combined)

    def test_visit_staleness_penalty(self):
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO households (id, name, village) VALUES ('hh-04', 'Kamla Devi', 'Rampur')"
        )
        # Last visit 60 days ago
        cursor.execute(
            "INSERT INTO mothers (id, household_id, last_visit_date) VALUES ('m-04', 'hh-04', '2026-07-05')"
        )
        self.db.commit()

        result = self.engine.evaluate_household("hh-04", self.db, reference_date=self.ref_date)
        self.assertIsNotNone(result)
        self.assertGreater(result.score, 0.0)
        self.assertTrue(any("60 दिन" in r for r in result.reasons))

    def test_ranking_orders_by_urgency_and_persists_to_db(self):
        cursor = self.db.cursor()
        # Household A: Normal
        cursor.execute("INSERT INTO households (id, name, village) VALUES ('hh-A', 'Calm Family', 'Rampur')")
        cursor.execute("INSERT INTO mothers (id, household_id, last_visit_date) VALUES ('mA', 'hh-A', '2026-08-30')")

        # Household B: Overdue Penta-3 (Score ~35)
        cursor.execute("INSERT INTO households (id, name, village) VALUES ('hh-B', 'Vaccine Overdue', 'Rampur')")
        cursor.execute(
            "INSERT INTO children (id, household_id, dob, dose_history_json) VALUES ('cB', 'hh-B', '2026-03-01', ?)",
            (json.dumps([{"vaccine": "Penta-3", "due_date": "2026-08-01", "date_given": None}]),)
        )

        # Household C: High Risk Mother (Score > 80)
        cursor.execute("INSERT INTO households (id, name, village) VALUES ('hh-C', 'Critical Mother', 'Rampur')")
        cursor.execute("INSERT INTO mothers (id, household_id, last_visit_date) VALUES ('mC', 'hh-C', '2026-08-01')")
        cursor.execute(
            "INSERT INTO anc_checkups (id, mother_id, date, bp, hb_level, danger_signs_json) VALUES ('ancC', 'mC', '2026-08-01', '150/100', 6.0, '[]')"
        )
        self.db.commit()

        # Refresh queue
        ranked = self.engine.refresh_priority_queue(self.db, reference_date=self.ref_date)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0].household_id, "hh-C")
        self.assertEqual(ranked[1].household_id, "hh-B")
        self.assertEqual(ranked[2].household_id, "hh-A")

        # Verify DB persistence in priority_queue table
        cursor.execute("SELECT household_id, score FROM priority_queue ORDER BY score DESC")
        rows = cursor.fetchall()
        self.assertEqual(rows[0][0], "hh-C")
        self.assertEqual(rows[1][0], "hh-B")
        self.assertEqual(rows[2][0], "hh-A")

        # Verify get_prioritized_households returns formatted payload
        list_output = self.engine.get_prioritized_households(self.db)
        self.assertEqual(list_output[0]["id"], "hh-C")
        self.assertEqual(list_output[0]["urgency_tier"], "HIGH")
        self.assertEqual(list_output[1]["id"], "hh-B")
        self.assertEqual(list_output[1]["urgency_tier"], "MEDIUM")
        self.assertEqual(list_output[2]["id"], "hh-A")
        self.assertEqual(list_output[2]["urgency_tier"], "LOW")


if __name__ == "__main__":
    unittest.main()
