"""Deterministic household prioritization engine for ASHA workers.
Evaluates vaccine delays, maternal risk flags, ANC checkups, visit staleness,
and scheme enrollment status directly from SQLite records without hardcoded values.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


def parse_date(date_str: str | None) -> date | None:
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def safe_json_list(raw: Any) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


@dataclass(frozen=True)
class PrioritizationResult:
    household_id: str
    household_name: str
    village: str
    score: float
    urgency_tier: str  # "HIGH", "MEDIUM", "LOW"
    reasons: list[str]
    last_computed: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "household_id": self.household_id,
            "household_name": self.household_name,
            "village": self.village,
            "score": self.score,
            "urgency_tier": self.urgency_tier,
            "reasons": self.reasons,
            "last_computed": self.last_computed,
            "details": self.details,
        }


class PrioritizationEngine:
    """Computes an auditable urgency score for each household using clinical and visit signals."""

    # Urgency tier thresholds
    HIGH_THRESHOLD = 60.0
    MEDIUM_THRESHOLD = 30.0

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else None

    def _get_connection(self, conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
        if conn is not None:
            return conn
        if self.db_path:
            return sqlite3.connect(self.db_path)
        raise ValueError("A database connection or db_path must be provided.")

    def evaluate_household(
        self,
        household_id: str,
        conn: sqlite3.Connection,
        reference_date: date | None = None,
    ) -> PrioritizationResult | None:
        ref = reference_date or date.today()
        cursor = conn.cursor()

        # 1. Fetch household info
        cursor.execute(
            "SELECT name, village, income_band, category, contact_notes FROM households WHERE id = ?",
            (household_id,),
        )
        hh_row = cursor.fetchone()
        if not hh_row:
            return None

        hh_name, village, income_band, category, contact_notes = hh_row
        score = 0.0
        reasons: list[str] = []
        details: dict[str, Any] = {
            "overdue_doses": [],
            "maternal_risks": [],
            "visit_staleness_days": None,
            "pending_schemes": [],
        }

        # 2. Check visit staleness from mothers or recent visits
        cursor.execute(
            "SELECT last_visit_date FROM mothers WHERE household_id = ? AND last_visit_date IS NOT NULL ORDER BY last_visit_date DESC LIMIT 1",
            (household_id,),
        )
        visit_row = cursor.fetchone()
        if visit_row and visit_row[0]:
            last_visit = parse_date(visit_row[0])
            if last_visit:
                days_unvisited = (ref - last_visit).days
                details["visit_staleness_days"] = days_unvisited
                if days_unvisited > 28:
                    staleness_pts = min(20.0, round((days_unvisited - 28) * 0.5, 1))
                    score += staleness_pts
                    reasons.append(
                        f"अंतिम भेंट को {days_unvisited} दिन हो चुके हैं (No visit in {days_unvisited} days)"
                    )

        # 3. Check immunization overdue status from children records
        cursor.execute(
            "SELECT id, dob, dose_history_json FROM children WHERE household_id = ?",
            (household_id,),
        )
        children = cursor.fetchall()
        for child_id, dob_str, dose_json in children:
            doses = safe_json_list(dose_json)
            for dose in doses:
                if not isinstance(dose, dict):
                    continue
                v_name = dose.get("vaccine", "टीका")
                date_given = parse_date(dose.get("date_given"))
                due_date = parse_date(dose.get("due_date"))

                # If dose not yet given and due_date has passed
                if not date_given and due_date and due_date <= ref:
                    days_overdue = (ref - due_date).days
                    details["overdue_doses"].append({"vaccine": v_name, "days_overdue": days_overdue})
                    if days_overdue >= 14:
                        score += 35.0
                        reasons.append(
                            f"{v_name} टीका {days_overdue} दिन से विलंबित (Overdue by {days_overdue} days)"
                        )
                    else:
                        score += 20.0
                        reasons.append(
                            f"{v_name} टीका {days_overdue} दिन से देय (Due by {days_overdue} days)"
                        )
                elif not date_given and due_date and 0 <= (due_date - ref).days <= 7:
                    days_left = (due_date - ref).days
                    score += 5.0
                    reasons.append(
                        f"{v_name} टीका {days_left} दिनों में देय (Upcoming in {days_left} days)"
                    )

        # 4. Check pregnancy risk & ANC checkup readings
        cursor.execute(
            "SELECT id, age, lmp_date, anc_visit_count, risk_flags_json FROM mothers WHERE household_id = ?",
            (household_id,),
        )
        mothers = cursor.fetchall()
        for mother_id, age, lmp_str, anc_count, flags_raw in mothers:
            flags = safe_json_list(flags_raw)
            for flag in flags:
                flag_str = str(flag).strip()
                details["maternal_risks"].append(flag_str)
                score += 30.0
                reasons.append(f"मातृ जोखिम संकेत: {flag_str} (Maternal risk flag)")

            # Check ANC shortfall if pregnant
            lmp = parse_date(lmp_str)
            if lmp:
                gestational_weeks = max(0, (ref - lmp).days // 7)
                if gestational_weeks >= 28 and anc_count < 3:
                    score += 25.0
                    reasons.append(
                        f"तीसरी तिमाही ({gestational_weeks} सप्ताह): केवल {anc_count} एएनसी जांच हुई (ANC shortfall in 3rd trimester)"
                    )
                elif gestational_weeks >= 14 and anc_count < 1:
                    score += 15.0
                    reasons.append(
                        f"दूसरी तिमाही ({gestational_weeks} सप्ताह): कोई एएनसी जांच नहीं (No ANC recorded in 2nd trimester)"
                    )

            # Check latest ANC clinical checkup readings (BP, Hb, Danger signs)
            cursor.execute(
                "SELECT bp, hb_level, danger_signs_json, date FROM anc_checkups WHERE mother_id = ? ORDER BY date DESC LIMIT 1",
                (mother_id,),
            )
            anc_row = cursor.fetchone()
            if anc_row:
                bp_str, hb, danger_raw, checkup_date = anc_row
                # BP check
                if bp_str:
                    try:
                        parts = bp_str.replace(" ", "").split("/")
                        systolic = int(parts[0])
                        diastolic = int(parts[1]) if len(parts) > 1 else 0
                        if systolic >= 140 or diastolic >= 90:
                            score += 40.0
                            reasons.append(
                                f"उच्च रक्तचाप ({bp_str}) — प्री-एक्लेम्पसिया जोखिम (High BP recorded)"
                            )
                    except (ValueError, IndexError):
                        pass

                # Anemia check
                if hb is not None:
                    try:
                        hb_val = float(hb)
                        if hb_val < 7.0:
                            score += 45.0
                            reasons.append(
                                f"गंभीर एनीमिया (Hb {hb_val} g/dL < 7.0) — तत्काल उपचार आवश्यक (Severe anemia)"
                            )
                        elif hb_val < 11.0:
                            score += 15.0
                            reasons.append(
                                f"एनीमिया (Hb {hb_val} g/dL) — आयरन/आईएफए अनुपूरक आवश्यक (Anemia)"
                            )
                    except (ValueError, TypeError):
                        pass

                # Danger signs check
                danger_signs = safe_json_list(danger_raw)
                for sign in danger_signs:
                    score += 45.0
                    reasons.append(f"गंभीर खतरे का लक्षण: {sign} (Danger sign recorded)")

        # 5. Check eligible but unclaimed government schemes
        cursor.execute(
            "SELECT scheme_name, next_action FROM scheme_matches WHERE household_id = ? AND eligible = 1",
            (household_id,),
        )
        schemes = cursor.fetchall()
        for s_name, next_action in schemes:
            details["pending_schemes"].append({"scheme": s_name, "next_action": next_action})
            score += 10.0
            reasons.append(f"योजना लाभ लंबित: {s_name} ({next_action})")

        # 6. Determine urgency tier
        final_score = round(score, 1)
        if final_score >= self.HIGH_THRESHOLD:
            urgency_tier = "HIGH"
        elif final_score >= self.MEDIUM_THRESHOLD:
            urgency_tier = "MEDIUM"
        else:
            urgency_tier = "LOW"

        # If low and no reasons generated, provide default calm state
        if not reasons:
            reasons.append("सभी नियमित स्वास्थ्य जांच एवं टीके पूर्ण (Routine - up to date)")

        now_iso = datetime.now().isoformat(timespec="seconds")

        return PrioritizationResult(
            household_id=household_id,
            household_name=hh_name,
            village=village,
            score=final_score,
            urgency_tier=urgency_tier,
            reasons=reasons,
            last_computed=now_iso,
            details=details,
        )

    def refresh_priority_queue(
        self,
        conn: sqlite3.Connection | None = None,
        reference_date: date | None = None,
    ) -> list[PrioritizationResult]:
        """Calculates urgency scores for all households in the database, saves to priority_queue table,
        and returns them sorted descending by score.
        """
        connection = self._get_connection(conn)
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM households")
        rows = cursor.fetchall()

        results: list[PrioritizationResult] = []
        for (hh_id,) in rows:
            res = self.evaluate_household(hh_id, connection, reference_date=reference_date)
            if res:
                results.append(res)
                cursor.execute(
                    """
                    INSERT INTO priority_queue (household_id, score, reasons_json, last_computed)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(household_id) DO UPDATE SET
                        score=excluded.score,
                        reasons_json=excluded.reasons_json,
                        last_computed=excluded.last_computed
                    """,
                    (res.household_id, res.score, json.dumps(res.reasons, ensure_ascii=False), res.last_computed),
                )

        connection.commit()
        # Sort descending by score, tie-breaker household name
        results.sort(key=lambda r: (r.score, r.household_name), reverse=True)
        return results

    def get_prioritized_households(
        self,
        conn: sqlite3.Connection | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Returns the current prioritized list from priority_queue joined with household metadata."""
        connection = self._get_connection(conn)
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT h.id, h.name, h.village, h.income_band, h.category, h.contact_notes,
                   pq.score, pq.reasons_json, pq.last_computed,
                   (SELECT last_visit_date FROM mothers m WHERE m.household_id = h.id ORDER BY m.last_visit_date DESC LIMIT 1) as last_visit,
                   (SELECT COUNT(*) FROM mothers m WHERE m.household_id = h.id) as mother_count,
                   (SELECT COUNT(*) FROM children c WHERE c.household_id = h.id) as child_count
            FROM priority_queue pq
            JOIN households h ON h.id = pq.household_id
            ORDER BY pq.score DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

        output: list[dict[str, Any]] = []
        for r in rows:
            hh_id, name, village, income, cat, notes, score, reasons_json, last_comp, last_visit, m_count, c_count = r
            score_val = float(score)
            tier = "HIGH" if score_val >= self.HIGH_THRESHOLD else ("MEDIUM" if score_val >= self.MEDIUM_THRESHOLD else "LOW")
            output.append({
                "id": hh_id,
                "name": name,
                "village": village,
                "income_band": income,
                "category": cat,
                "contact_notes": notes,
                "score": score_val,
                "urgency_tier": tier,
                "reasons": safe_json_list(reasons_json),
                "last_computed": last_comp,
                "last_visit_date": last_visit,
                "mother_count": m_count,
                "child_count": c_count,
            })
        return output
