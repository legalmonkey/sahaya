-- Day 1 shared local-only data schema. JSON arrays are stored as TEXT because
-- SQLite has no native array type; callers must validate their JSON payloads.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    village TEXT NOT NULL,
    income_band TEXT,
    category TEXT,
    contact_notes TEXT
);

CREATE TABLE IF NOT EXISTS mothers (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    age INTEGER,
    lmp_date TEXT,
    anc_visit_count INTEGER NOT NULL DEFAULT 0,
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    last_visit_date TEXT
);

CREATE TABLE IF NOT EXISTS children (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    dob TEXT NOT NULL,
    dose_history_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS anc_checkups (
    id TEXT PRIMARY KEY,
    mother_id TEXT NOT NULL REFERENCES mothers(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    bp TEXT,
    hb_level REAL,
    danger_signs_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scheme_matches (
    household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    scheme_name TEXT NOT NULL,
    eligible INTEGER NOT NULL CHECK (eligible IN (0, 1)),
    reason TEXT NOT NULL,
    next_action TEXT NOT NULL,
    PRIMARY KEY (household_id, scheme_name)
);

CREATE TABLE IF NOT EXISTS priority_queue (
    household_id TEXT PRIMARY KEY REFERENCES households(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    last_computed TEXT NOT NULL
);
