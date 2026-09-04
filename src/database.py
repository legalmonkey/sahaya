"""SQLite database manager and data access layer for Sahaya's shared schema (spec §3).

Provides schema initialization and helpers for households, mothers, children,
anc_checkups, scheme_matches, and priority_queue.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import SETTINGS


def get_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else SETTINGS.database_path
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | str | None = None, migration_path: Path | str | None = None) -> None:
    """Apply the shared schema migration if tables do not exist."""
    mig_path = Path(migration_path) if migration_path is not None else SETTINGS.schema_migration_path
    if not mig_path.exists():
        raise FileNotFoundError(f"Migration file not found at {mig_path}")

    sql = mig_path.read_text(encoding="utf-8")
    with get_db_connection(db_path) as conn:
        conn.executescript(sql)
        conn.commit()


def get_child(child_id: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    """Fetch child record and parse dose_history as a Python list."""
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, household_id, dob, dose_history FROM children WHERE id = ?",
            (child_id,),
        ).fetchone()
        if not row:
            return None

        dose_hist_raw = row["dose_history"]
        if isinstance(dose_hist_raw, str):
            try:
                dose_history = json.loads(dose_hist_raw)
            except Exception:
                dose_history = []
        elif isinstance(dose_hist_raw, list):
            dose_history = dose_hist_raw
        else:
            dose_history = []

        return {
            "id": row["id"],
            "household_id": row["household_id"],
            "dob": row["dob"],
            "dose_history": dose_history,
        }


def upsert_child(
    child_id: str,
    household_id: str,
    dob: str,
    dose_history: list[dict] | str,
    db_path: Path | str | None = None,
) -> None:
    """Insert or update a child record in the shared schema."""
    if not isinstance(dose_history, str):
        dose_history_json = json.dumps(dose_history)
    else:
        dose_history_json = dose_history

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO children (id, household_id, dob, dose_history)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                household_id = excluded.household_id,
                dob = excluded.dob,
                dose_history = excluded.dose_history
            """,
            (child_id, household_id, dob, dose_history_json),
        )
        conn.commit()


def upsert_household(
    household_id: str,
    name: str,
    village: str,
    income_band: str = "BPL",
    category: str = "SC",
    contact_notes: str = "",
    db_path: Path | str | None = None,
) -> None:
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO households (id, name, village, income_band, category, contact_notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                village = excluded.village,
                income_band = excluded.income_band,
                category = excluded.category,
                contact_notes = excluded.contact_notes
            """,
            (household_id, name, village, income_band, category, contact_notes),
        )
        conn.commit()


def list_children(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, household_id, dob, dose_history FROM children ORDER BY id"
        ).fetchall()
        result = []
        for r in rows:
            dh = r["dose_history"]
            if isinstance(dh, str):
                try:
                    dh = json.loads(dh)
                except Exception:
                    dh = []
            result.append({
                "id": r["id"],
                "household_id": r["household_id"],
                "dob": r["dob"],
                "dose_history": dh,
            })
        return result


def seed_demo_data(db_path: Path | str | None = None) -> None:
    """Seed realistic demo households and child vaccination cases."""
    init_db(db_path)
    
    # Households
    upsert_household("hh_001", "Meena Devi", "Rampur", "BPL", "OBC", "Near primary school", db_path=db_path)
    upsert_household("hh_002", "Sunita Sharma", "Rampur", "APL", "General", "House #12", db_path=db_path)
    upsert_household("hh_003", "Kavita Bai", "Shivpur", "BPL", "SC", "Near anganwadi center", db_path=db_path)
    upsert_household("hh_004", "Geeta Patel", "Shivpur", "BPL", "ST", "Main road", db_path=db_path)

    # Child 1: Newborn (DOB: 7 days ago) — Received birth doses
    # Assuming reference date approx 2026-09-01
    upsert_child(
        child_id="child_001",
        household_id="hh_001",
        dob="2026-08-25",
        dose_history=[
            {"vaccine": "BCG", "date_given": "2026-08-25", "due_date": "2026-08-25"},
            {"vaccine": "OPV-0", "date_given": "2026-08-25", "due_date": "2026-08-25"},
            {"vaccine": "HepB-0", "date_given": "2026-08-25", "due_date": "2026-08-25"},
        ],
        db_path=db_path,
    )

    # Child 2: 6-month-old infant with missed/overdue 6-week & 10-week doses
    upsert_child(
        child_id="child_002",
        household_id="hh_002",
        dob="2026-03-01",
        dose_history=[
            {"vaccine": "BCG", "date_given": "2026-03-01", "due_date": "2026-03-01"},
            {"vaccine": "OPV-0", "date_given": "2026-03-01", "due_date": "2026-03-01"},
            {"vaccine": "HepB-0", "date_given": "2026-03-01", "due_date": "2026-03-01"},
            # Missed 6w, 10w, 14w doses
        ],
        db_path=db_path,
    )

    # Child 3: 10-month-old infant up to date on primary doses, due for MR-1 & Vitamin A
    upsert_child(
        child_id="child_003",
        household_id="hh_003",
        dob="2025-11-01",
        dose_history=[
            {"vaccine": "BCG", "date_given": "2025-11-01", "due_date": "2025-11-01"},
            {"vaccine": "OPV-0", "date_given": "2025-11-01", "due_date": "2025-11-01"},
            {"vaccine": "HepB-0", "date_given": "2025-11-01", "due_date": "2025-11-01"},
            {"vaccine": "Pentavalent-1", "date_given": "2025-12-15", "due_date": "2025-12-13"},
            {"vaccine": "OPV-1", "date_given": "2025-12-15", "due_date": "2025-12-13"},
            {"vaccine": "Rotavirus-1", "date_given": "2025-12-15", "due_date": "2025-12-13"},
            {"vaccine": "fIPV-1", "date_given": "2025-12-15", "due_date": "2025-12-13"},
            {"vaccine": "Pentavalent-2", "date_given": "2026-01-15", "due_date": "2026-01-10"},
            {"vaccine": "OPV-2", "date_given": "2026-01-15", "due_date": "2026-01-10"},
            {"vaccine": "Rotavirus-2", "date_given": "2026-01-15", "due_date": "2026-01-10"},
            {"vaccine": "Pentavalent-3", "date_given": "2026-02-20", "due_date": "2026-02-07"},
            {"vaccine": "OPV-3", "date_given": "2026-02-20", "due_date": "2026-02-07"},
            {"vaccine": "Rotavirus-3", "date_given": "2026-02-20", "due_date": "2026-02-07"},
            {"vaccine": "fIPV-2", "date_given": "2026-02-20", "due_date": "2026-02-07"},
        ],
        db_path=db_path,
    )

    # Child 4: Newborn with NO vaccination history at all
    upsert_child(
        child_id="child_004",
        household_id="hh_004",
        dob="2026-08-20",
        dose_history=[],
        db_path=db_path,
    )
