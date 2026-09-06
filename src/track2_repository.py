"""SQLite integration for Track 2. Only raw inputs are seeded; results are computed live."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.track2 import Track2Service


class Track2Repository:
    def __init__(self, database_path: Path, service: Track2Service):
        self.database_path = database_path
        self.service = service

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def seed_demo_inputs(self) -> None:
        """Synthetic raw facts only; no computed risk or scheme output is inserted."""
        with self._connection() as connection:
            if connection.execute("SELECT 1 FROM households LIMIT 1").fetchone():
                return
            connection.execute(
                """INSERT INTO households (id,name,village,income_band,category,contact_notes,annual_income_inr,
                   has_bpl_ration_card,has_nfsa_ration_card,has_e_shram_card,has_mgnrega_job_card,
                   is_pm_kisan_beneficiary,is_pmjay_listed,is_disabled_40_percent,has_pmmvy_eligible_worker,state)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("demo-hh-001", "Meena Devi household", "Demo village", "below_8_lakh", "SC", "Synthetic demo input", 240000,
                 1, 0, 0, 0, 0, 0, 0, 0, "Bihar"),
            )
            connection.execute(
                """INSERT INTO mothers (id,household_id,age,lmp_date,anc_visit_count,risk_flags_json,last_visit_date,
                   is_pregnant,is_lactating,trimester,planned_delivery_facility)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                ("demo-mother-001", "demo-hh-001", 24, "2026-02-15", 1, "[]", "2026-08-18", 1, 0, 3, "government"),
            )
            connection.execute(
                """INSERT INTO anc_checkups (id,mother_id,date,bp,hb_level,danger_signs_json,notes)
                   VALUES (?,?,?,?,?,?,?)""",
                ("demo-anc-001", "demo-mother-001", "2026-09-01", "146/94", 9.6, "[\"severe headache with blurred vision\"]", "Synthetic raw ANC input"),
            )
            connection.execute("INSERT INTO children (id,household_id,dob,dose_history_json) VALUES (?,?,?,?)", ("demo-child-001", "demo-hh-001", "2023-07-14", "[]"))

    def household_view(self, household_id: str) -> dict:
        with self._connection() as connection:
            household = connection.execute("SELECT * FROM households WHERE id=?", (household_id,)).fetchone()
            if household is None:
                raise ValueError("Household was not found.")
            mother = connection.execute("SELECT * FROM mothers WHERE household_id=? ORDER BY id LIMIT 1", (household_id,)).fetchone()
            children = connection.execute("SELECT * FROM children WHERE household_id=?", (household_id,)).fetchall()
            return {"household": dict(household), "mother": dict(mother) if mother else None, "children": [dict(item) for item in children]}

    def evaluate_and_persist(self, household_id: str) -> dict:
        view = self.household_view(household_id)
        if not view["mother"]:
            raise ValueError("The household has no mother record for Track 2 assessment.")
        with self._connection() as connection:
            checkup = connection.execute("SELECT * FROM anc_checkups WHERE mother_id=? ORDER BY date DESC LIMIT 1", (view["mother"]["id"],)).fetchone()
        if checkup is None:
            raise ValueError("The mother has no ANC checkup for Track 2 assessment.")
        mother = dict(view["mother"])
        anc = dict(checkup); anc["danger_signs"] = json.loads(anc.pop("danger_signs_json"))
        risk = self.service.assess_risk(mother, anc)
        eligibility = self.service.assess_eligibility(view["household"], mother, view["children"])
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute("UPDATE mothers SET risk_flags_json=? WHERE id=?", (json.dumps(risk["risk_flags"]), mother["id"]))
            connection.execute("DELETE FROM scheme_matches WHERE household_id=?", (household_id,))
            for match in eligibility["scheme_matches"]:
                connection.execute("INSERT INTO scheme_matches (household_id,scheme_name,eligible,reason,next_action) VALUES (?,?,?,?,?)", (
                    household_id, match["scheme_name"], int(match["eligible"]), json.dumps(match["reason"]), json.dumps(match["next_action"])))
        return {"evaluated_at": now, "risk": risk, "eligibility": eligibility}
