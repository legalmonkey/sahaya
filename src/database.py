"""Local SQLite initialisation from the single shared Day 1 migration."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def initialise(database_path: Path, migration_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.executescript(migration_path.read_text(encoding="utf-8"))
