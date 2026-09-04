package com.sahaya.app.data.local

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class SahayaDbHelper(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        const val DATABASE_NAME = "sahaya.db"
        const val DATABASE_VERSION = 1
        private val gson = Gson()
    }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS households (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                village TEXT NOT NULL,
                income_band TEXT,
                category TEXT,
                contact_notes TEXT
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS mothers (
                id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
                age INTEGER,
                lmp_date TEXT,
                anc_visit_count INTEGER NOT NULL DEFAULT 0,
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                last_visit_date TEXT
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS children (
                id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
                dob TEXT NOT NULL,
                dose_history_json TEXT NOT NULL DEFAULT '[]'
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS anc_checkups (
                id TEXT PRIMARY KEY,
                mother_id TEXT NOT NULL REFERENCES mothers(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                bp TEXT,
                hb_level REAL,
                danger_signs_json TEXT NOT NULL DEFAULT '[]',
                notes TEXT
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS scheme_matches (
                household_id TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
                scheme_name TEXT NOT NULL,
                eligible INTEGER NOT NULL CHECK (eligible IN (0, 1)),
                reason TEXT NOT NULL,
                next_action TEXT NOT NULL,
                PRIMARY KEY (household_id, scheme_name)
            );
        """.trimIndent())

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS priority_queue (
                household_id TEXT PRIMARY KEY REFERENCES households(id) ON DELETE CASCADE,
                score REAL NOT NULL,
                reasons_json TEXT NOT NULL DEFAULT '[]',
                last_computed TEXT NOT NULL
            );
        """.trimIndent())

        seedFigmaDemoHouseholds(db)
    }

    override fun onOpen(db: SQLiteDatabase) {
        super.onOpen(db)
        seedFigmaDemoHouseholds(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Shared schema migration strategy
    }

    fun seedFigmaDemoHouseholds(db: SQLiteDatabase) {
        val cursor = db.rawQuery("SELECT COUNT(*) FROM households", null)
        var count = 0
        cursor.use {
            if (it.moveToNext()) count = it.getInt(0)
        }
        if (count > 0) return // Already seeded

        db.beginTransaction()
        try {
            // 1. Meena Devi's Family (Pipra Village, Household ID: 409) - CRITICAL
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_409', 'Meena Devi''s Family', 'Pipra Village', 'BPL', 'OBC', 'Household ID: 409');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO mothers (id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date)
                VALUES ('m_409', 'hh_409', 24, '2025-04-10', 3, '["Anemia detected (Hb 9.5)"]', '2026-01-15');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO anc_checkups (id, mother_id, date, bp, hb_level, danger_signs_json, notes)
                VALUES ('chk_409', 'm_409', '2026-01-15', '120/80', 9.5, '["Anemia detected"]', 'High Risk - Anemia detected (Hb 9.5)');
            """.trimIndent())
            val dosesAarav = """[
                {"vaccine":"BCG","date_given":"2025-07-02","due_date":"2025-07-01"},
                {"vaccine":"OPV-1","date_given":"2025-08-15","due_date":"2025-08-15"},
                {"vaccine":"Penta-1","date_given":"2025-08-15","due_date":"2025-08-15"},
                {"vaccine":"Penta-2","date_given":"2025-09-20","due_date":"2025-09-20"},
                {"vaccine":"Pentavalent-3","date_given":null,"due_date":"2026-01-12"}
            ]"""
            val cvChild = ContentValues().apply {
                put("id", "c_409")
                put("household_id", "hh_409")
                put("dob", "2025-07-01")
                put("dose_history_json", dosesAarav)
            }
            db.insert("children", null, cvChild)
            db.execSQL("""
                INSERT INTO scheme_matches (household_id, scheme_name, eligible, reason, next_action)
                VALUES ('hh_409', 'PMMVY', 1, 'First child institutional delivery benefit', '2 Schemes Eligible (PMMVY, JSY)');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO scheme_matches (household_id, scheme_name, eligible, reason, next_action)
                VALUES ('hh_409', 'JSY', 1, 'Institutional delivery cash assistance', 'Documents required');
            """.trimIndent())

            // 2. Sunita Bai's Family (Pipra Village) - ATTENTION
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_410', 'Sunita Bai''s Family', 'Pipra Village', 'APL', 'General', 'Near Primary School');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO mothers (id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date)
                VALUES ('m_410', 'hh_410', 26, '2026-03-01', 0, '["Missed ANC checkup (2nd Trimester)"]', '2026-06-01');
            """.trimIndent())

            // 3. Radha Yadav's Family (Khas Tola) - ON TRACK
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_411', 'Radha Yadav''s Family', 'Khas Tola', 'BPL', 'OBC', 'Next visit scheduled 12 Feb');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO mothers (id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date)
                VALUES ('m_411', 'hh_411', 28, null, 4, '[]', '2026-08-25');
            """.trimIndent())
            val dosesRadha = """[
                {"vaccine":"BCG","date_given":"2026-01-05","due_date":"2026-01-01"},
                {"vaccine":"OPV-1","date_given":"2026-02-15","due_date":"2026-02-15"},
                {"vaccine":"Penta-1","date_given":"2026-02-15","due_date":"2026-02-15"}
            ]"""
            val cvRadhaChild = ContentValues().apply {
                put("id", "c_411")
                put("household_id", "hh_411")
                put("dob", "2026-01-01")
                put("dose_history_json", dosesRadha)
            }
            db.insert("children", null, cvRadhaChild)

            // 4. Geeta Sharma's Family (Khas Tola) - CRITICAL
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_412', 'Geeta Sharma''s Family', 'Khas Tola', 'BPL', 'General', 'Severe Anemia warning');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO mothers (id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date)
                VALUES ('m_412', 'hh_412', 22, '2026-01-10', 1, '["Severe Anemia (Hb 6.8 < 7.0)"]', '2026-08-01');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO anc_checkups (id, mother_id, date, bp, hb_level, danger_signs_json, notes)
                VALUES ('chk_412', 'm_412', '2026-08-01', '135/88', 6.8, '["Severe Anemia"]', 'Severe Anemia warning — Needs IFA follow-up');
            """.trimIndent())

            // 5. Kavita Devi's Family (Pipra Tola 1) - ATTENTION
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_413', 'Kavita Devi''s Family', 'Pipra Tola 1', 'BPL', 'SC', 'Newborn child');
            """.trimIndent())
            val dosesKavita = """[
                {"vaccine":"Hepatitis B (Birth dose)","date_given":null,"due_date":"2026-08-26"},
                {"vaccine":"BCG","date_given":null,"due_date":"2026-08-26"}
            ]"""
            val cvKavita = ContentValues().apply {
                put("id", "c_413")
                put("household_id", "hh_413")
                put("dob", "2026-08-25")
                put("dose_history_json", dosesKavita)
            }
            db.insert("children", null, cvKavita)

            // 6. Anita Kumari's Family (Khas Tola) - ON TRACK
            db.execSQL("""
                INSERT INTO households (id, name, village, income_band, category, contact_notes)
                VALUES ('hh_414', 'Anita Kumari''s Family', 'Khas Tola', 'APL', 'OBC', 'Routine post-natal follow up');
            """.trimIndent())
            db.execSQL("""
                INSERT INTO mothers (id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date)
                VALUES ('m_414', 'hh_414', 25, null, 4, '[]', '2026-08-28');
            """.trimIndent())

            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun insertHousehold(h: Household) {
        val cv = ContentValues().apply {
            put("id", h.id)
            put("name", h.name)
            put("village", h.village)
            put("income_band", h.incomeBand)
            put("category", h.category)
            put("contact_notes", h.contactNotes)
        }
        writableDatabase.insertWithOnConflict("households", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun insertMother(m: Mother) {
        val cv = ContentValues().apply {
            put("id", m.id)
            put("household_id", m.householdId)
            put("age", m.age)
            put("lmp_date", m.lmpDate)
            put("anc_visit_count", m.ancVisitCount)
            put("risk_flags_json", gson.toJson(m.riskFlags))
            put("last_visit_date", m.lastVisitDate)
        }
        writableDatabase.insertWithOnConflict("mothers", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun insertChild(c: Child) {
        val cv = ContentValues().apply {
            put("id", c.id)
            put("household_id", c.householdId)
            put("dob", c.dob)
            put("dose_history_json", gson.toJson(c.doseHistory))
        }
        writableDatabase.insertWithOnConflict("children", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun insertAncCheckup(chk: AncCheckup) {
        val cv = ContentValues().apply {
            put("id", chk.id)
            put("mother_id", chk.motherId)
            put("date", chk.date)
            put("bp", chk.bp)
            put("hb_level", chk.hbLevel)
            put("danger_signs_json", gson.toJson(chk.dangerSigns))
            put("notes", chk.notes)
        }
        writableDatabase.insertWithOnConflict("anc_checkups", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun insertSchemeMatch(s: SchemeMatch) {
        val cv = ContentValues().apply {
            put("household_id", s.householdId)
            put("scheme_name", s.schemeName)
            put("eligible", if (s.eligible) 1 else 0)
            put("reason", s.reason)
            put("next_action", s.nextAction)
        }
        writableDatabase.insertWithOnConflict("scheme_matches", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun getAllHouseholds(): List<Household> {
        val list = mutableListOf<Household>()
        val cursor = readableDatabase.rawQuery("SELECT id, name, village, income_band, category, contact_notes FROM households", null)
        cursor.use {
            while (it.moveToNext()) {
                list.add(
                    Household(
                        id = it.getString(0),
                        name = it.getString(1),
                        village = it.getString(2),
                        incomeBand = it.getString(3),
                        category = it.getString(4),
                        contactNotes = it.getString(5)
                    )
                )
            }
        }
        return list
    }

    fun getHouseholdDetails(id: String): Map<String, Any?>? {
        val db = readableDatabase
        val hCursor = db.rawQuery("SELECT id, name, village, income_band, category, contact_notes FROM households WHERE id = ?", arrayOf(id))
        var household: Household? = null
        hCursor.use {
            if (it.moveToNext()) {
                household = Household(it.getString(0), it.getString(1), it.getString(2), it.getString(3), it.getString(4), it.getString(5))
            }
        }
        if (household == null) return null

        val mothers = mutableListOf<Mother>()
        val mCursor = db.rawQuery("SELECT id, household_id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date FROM mothers WHERE household_id = ?", arrayOf(id))
        val stringListType = object : TypeToken<List<String>>() {}.type
        mCursor.use {
            while (it.moveToNext()) {
                val mId = it.getString(0)
                val checkups = mutableListOf<AncCheckup>()
                val chkCursor = db.rawQuery("SELECT id, mother_id, date, bp, hb_level, danger_signs_json, notes FROM anc_checkups WHERE mother_id = ? ORDER BY date DESC", arrayOf(mId))
                chkCursor.use { cIt ->
                    while (cIt.moveToNext()) {
                        checkups.add(
                            AncCheckup(
                                id = cIt.getString(0),
                                motherId = cIt.getString(1),
                                date = cIt.getString(2),
                                bp = cIt.getString(3),
                                hbLevel = if (cIt.isNull(4)) null else cIt.getDouble(4),
                                dangerSigns = gson.fromJson(cIt.getString(5) ?: "[]", stringListType) ?: emptyList(),
                                notes = cIt.getString(6)
                            )
                        )
                    }
                }

                mothers.add(
                    Mother(
                        id = mId,
                        householdId = it.getString(1),
                        age = if (it.isNull(2)) null else it.getInt(2),
                        lmpDate = it.getString(3),
                        ancVisitCount = it.getInt(4),
                        riskFlags = gson.fromJson(it.getString(5) ?: "[]", stringListType) ?: emptyList(),
                        lastVisitDate = it.getString(6),
                        checkups = checkups
                    )
                )
            }
        }

        val children = mutableListOf<Child>()
        val cCursor = db.rawQuery("SELECT id, household_id, dob, dose_history_json FROM children WHERE household_id = ?", arrayOf(id))
        val doseListType = object : TypeToken<List<VaccineDose>>() {}.type
        cCursor.use {
            while (it.moveToNext()) {
                children.add(
                    Child(
                        id = it.getString(0),
                        householdId = it.getString(1),
                        dob = it.getString(2),
                        doseHistory = gson.fromJson(it.getString(3) ?: "[]", doseListType) ?: emptyList()
                    )
                )
            }
        }

        val schemes = mutableListOf<SchemeMatch>()
        val sCursor = db.rawQuery("SELECT household_id, scheme_name, eligible, reason, next_action FROM scheme_matches WHERE household_id = ?", arrayOf(id))
        sCursor.use {
            while (it.moveToNext()) {
                schemes.add(
                    SchemeMatch(
                        householdId = it.getString(0),
                        schemeName = it.getString(1),
                        eligible = it.getInt(2) == 1,
                        reason = it.getString(3),
                        nextAction = it.getString(4)
                    )
                )
            }
        }

        return mapOf(
            "household" to household,
            "mothers" to mothers,
            "children" to children,
            "schemes" to schemes
        )
    }
}
