-- Sahaya Shared Schema Migration 001
-- Tables: households, mothers, children, anc_checkups, scheme_matches, priority_queue

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
    household_id TEXT NOT NULL REFERENCES households(id),
    age INTEGER,
    lmp_date TEXT,
    anc_visit_count INTEGER DEFAULT 0,
    risk_flags TEXT DEFAULT '[]',
    last_visit_date TEXT
);

CREATE TABLE IF NOT EXISTS children (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    dob TEXT NOT NULL,
    dose_history TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS anc_checkups (
    id TEXT PRIMARY KEY,
    mother_id TEXT NOT NULL REFERENCES mothers(id),
    date TEXT NOT NULL,
    bp TEXT,
    hb_level REAL,
    danger_signs TEXT DEFAULT '[]',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scheme_matches (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    scheme_name TEXT NOT NULL,
    eligible INTEGER NOT NULL,
    reason TEXT,
    next_action TEXT
);

CREATE TABLE IF NOT EXISTS priority_queue (
    household_id TEXT PRIMARY KEY REFERENCES households(id),
    score REAL NOT NULL,
    reasons TEXT DEFAULT '[]',
    last_computed TEXT NOT NULL
);
