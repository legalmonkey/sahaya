package com.sahaya.app.domain.prioritization

import android.content.ContentValues
import android.database.sqlite.SQLiteDatabase
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.sahaya.app.data.local.PrioritizedHousehold
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

class PrioritizationEngine {

    companion object {
        const val HIGH_THRESHOLD = 60.0
        const val MEDIUM_THRESHOLD = 30.0
        private val DATE_FORMAT = SimpleDateFormat("yyyy-MM-dd", Locale.US)
        private val gson = Gson()
    }

    private fun parseDate(dateStr: String?): Date? {
        if (dateStr.isNullOrBlank()) return null
        return try {
            val clean = if (dateStr.length >= 10) dateStr.substring(0, 10) else dateStr
            DATE_FORMAT.parse(clean)
        } catch (e: Exception) {
            null
        }
    }

    private fun daysBetween(start: Date, end: Date): Int {
        val diff = end.time - start.time
        return (diff / (1000 * 60 * 60 * 24)).toInt()
    }

    fun evaluateHousehold(
        householdId: String,
        db: SQLiteDatabase,
        referenceDate: Date = Date()
    ): PrioritizedHousehold? {
        val hCursor = db.rawQuery(
            "SELECT name, village, income_band, category, contact_notes FROM households WHERE id = ?",
            arrayOf(householdId)
        )
        var name = ""
        var village = ""
        var incomeBand: String? = null
        var category: String? = null
        var contactNotes: String? = null

        hCursor.use {
            if (!it.moveToNext()) return null
            name = it.getString(0)
            village = it.getString(1)
            incomeBand = it.getString(2)
            category = it.getString(3)
            contactNotes = it.getString(4)
        }

        var score = 0.0
        val reasons = mutableListOf<String>()
        var lastVisitStr: String? = null

        // 1. Visit staleness
        val vCursor = db.rawQuery(
            "SELECT last_visit_date FROM mothers WHERE household_id = ? AND last_visit_date IS NOT NULL ORDER BY last_visit_date DESC LIMIT 1",
            arrayOf(householdId)
        )
        vCursor.use {
            if (it.moveToNext()) {
                lastVisitStr = it.getString(0)
                val lv = parseDate(lastVisitStr)
                if (lv != null) {
                    val daysUnvisited = daysBetween(lv, referenceDate)
                    if (daysUnvisited > 28) {
                        val pts = min(20.0, (daysUnvisited - 28) * 0.5)
                        score += pts
                        reasons.add("अंतिम भेंट को $daysUnvisited दिन हो चुके हैं (No visit in $daysUnvisited days)")
                    }
                }
            }
        }

        // 2. Child immunization status
        var childCount = 0
        val cCursor = db.rawQuery(
            "SELECT id, dob, dose_history_json FROM children WHERE household_id = ?",
            arrayOf(householdId)
        )
        val doseListType = object : TypeToken<List<Map<String, Any?>>>() {}.type
        cCursor.use {
            while (it.moveToNext()) {
                childCount++
                val doseRaw = it.getString(2) ?: "[]"
                val doses: List<Map<String, Any?>> = try {
                    gson.fromJson(doseRaw, doseListType) ?: emptyList()
                } catch (e: Exception) {
                    emptyList()
                }

                for (dose in doses) {
                    val vName = (dose["vaccine"] as? String) ?: "टीका"
                    val dateGiven = parseDate(dose["date_given"] as? String)
                    val dueDate = parseDate(dose["due_date"] as? String)

                    if (dateGiven == null && dueDate != null) {
                        if (dueDate.before(referenceDate) || dueDate == referenceDate) {
                            val daysOverdue = daysBetween(dueDate, referenceDate)
                            if (daysOverdue >= 14) {
                                score += 35.0
                                reasons.add("$vName टीका $daysOverdue दिन से विलंबित (Overdue by $daysOverdue days)")
                            } else {
                                score += 20.0
                                reasons.add("$vName टीका $daysOverdue दिन से देय (Due by $daysOverdue days)")
                            }
                        } else {
                            val daysLeft = daysBetween(referenceDate, dueDate)
                            if (daysLeft in 0..7) {
                                score += 5.0
                                reasons.add("$vName टीका $daysLeft दिनों में देय (Upcoming in $daysLeft days)")
                            }
                        }
                    }
                }
            }
        }

        // 3. Maternal risk & ANC checkup readings
        var motherCount = 0
        val mCursor = db.rawQuery(
            "SELECT id, age, lmp_date, anc_visit_count, risk_flags_json FROM mothers WHERE household_id = ?",
            arrayOf(householdId)
        )
        val stringListType = object : TypeToken<List<String>>() {}.type
        mCursor.use {
            while (it.moveToNext()) {
                motherCount++
                val mId = it.getString(0)
                val lmpStr = it.getString(2)
                val ancCount = it.getInt(3)
                val flagsRaw = it.getString(4) ?: "[]"
                val flags: List<String> = try {
                    gson.fromJson(flagsRaw, stringListType) ?: emptyList()
                } catch (e: Exception) {
                    emptyList()
                }

                for (flag in flags) {
                    score += 30.0
                    reasons.add("मातृ जोखिम संकेत: $flag (Maternal risk flag)")
                }

                val lmp = parseDate(lmpStr)
                if (lmp != null) {
                    val gestationalWeeks = max(0, daysBetween(lmp, referenceDate) / 7)
                    if (gestationalWeeks >= 28 && ancCount < 3) {
                        score += 25.0
                        reasons.add("तीसरी तिमाही ($gestationalWeeks सप्ताह): केवल $ancCount एएनसी जांच हुई (ANC shortfall)")
                    } else if (gestationalWeeks >= 14 && ancCount < 1) {
                        score += 15.0
                        reasons.add("दूसरी तिमाही ($gestationalWeeks सप्ताह): कोई एएनसी जांच दर्ज नहीं (No ANC in 2nd trimester)")
                    }
                }

                val chkCursor = db.rawQuery(
                    "SELECT bp, hb_level, danger_signs_json FROM anc_checkups WHERE mother_id = ? ORDER BY date DESC LIMIT 1",
                    arrayOf(mId)
                )
                chkCursor.use { cIt ->
                    if (cIt.moveToNext()) {
                        val bpStr = cIt.getString(0)
                        val hb = if (cIt.isNull(1)) null else cIt.getDouble(1)
                        val dangerRaw = cIt.getString(2) ?: "[]"
                        val dangerSigns: List<String> = try {
                            gson.fromJson(dangerRaw, stringListType) ?: emptyList()
                        } catch (e: Exception) {
                            emptyList()
                        }

                        if (!bpStr.isNullOrBlank()) {
                            val parts = bpStr.replace(" ", "").split("/")
                            if (parts.isNotEmpty()) {
                                val systolic = parts[0].toIntOrNull() ?: 0
                                val diastolic = if (parts.size > 1) parts[1].toIntOrNull() ?: 0 else 0
                                if (systolic >= 140 || diastolic >= 90) {
                                    score += 40.0
                                    reasons.add("उच्च रक्तचाप ($bpStr) — प्री-एक्लेम्पसिया जोखिम (High BP recorded)")
                                }
                            }
                        }

                        if (hb != null) {
                            if (hb < 7.0) {
                                score += 45.0
                                reasons.add("गंभीर एनीमिया (Hb $hb g/dL < 7.0) — तत्काल उपचार आवश्यक (Severe anemia)")
                            } else if (hb < 11.0) {
                                score += 15.0
                                reasons.add("एनीमिया (Hb $hb g/dL) — आईएफए अनुपूरक आवश्यक (Anemia)")
                            }
                        }

                        for (sign in dangerSigns) {
                            score += 45.0
                            reasons.add("गंभीर खतरे का लक्षण: $sign (Danger sign)")
                        }
                    }
                }
            }
        }

        // 4. Scheme matches
        val sCursor = db.rawQuery(
            "SELECT scheme_name, next_action FROM scheme_matches WHERE household_id = ? AND eligible = 1",
            arrayOf(householdId)
        )
        sCursor.use {
            while (it.moveToNext()) {
                val sName = it.getString(0)
                val nextAction = it.getString(1)
                score += 10.0
                reasons.add("योजना लाभ लंबित: $sName ($nextAction)")
            }
        }

        val finalScore = (score * 10.0).toInt() / 10.0
        val tier = when {
            finalScore >= HIGH_THRESHOLD -> "HIGH"
            finalScore >= MEDIUM_THRESHOLD -> "MEDIUM"
            else -> "LOW"
        }

        if (reasons.isEmpty()) {
            reasons.add("सभी नियमित स्वास्थ्य जांच एवं टीके पूर्ण (Routine - up to date)")
        }

        return PrioritizedHousehold(
            id = householdId,
            name = name,
            village = village,
            incomeBand = incomeBand,
            category = category,
            score = finalScore,
            urgencyTier = tier,
            reasons = reasons,
            lastVisitDate = lastVisitStr,
            motherCount = motherCount,
            childCount = childCount
        )
    }

    fun refreshPriorityQueue(db: SQLiteDatabase, referenceDate: Date = Date()): List<PrioritizedHousehold> {
        val households = mutableListOf<String>()
        val cursor = db.rawQuery("SELECT id FROM households", null)
        cursor.use {
            while (it.moveToNext()) {
                households.add(it.getString(0))
            }
        }

        val results = mutableListOf<PrioritizedHousehold>()
        val nowIso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(referenceDate)

        db.beginTransaction()
        try {
            for (hId in households) {
                val res = evaluateHousehold(hId, db, referenceDate)
                if (res != null) {
                    results.add(res)
                    val cv = ContentValues().apply {
                        put("household_id", res.id)
                        put("score", res.score)
                        put("reasons_json", gson.toJson(res.reasons))
                        put("last_computed", nowIso)
                    }
                    db.insertWithOnConflict("priority_queue", null, cv, SQLiteDatabase.CONFLICT_REPLACE)
                }
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }

        return results.sortedWith(compareByDescending<PrioritizedHousehold> { it.score }.thenBy { it.name })
    }

    fun getPrioritizedHouseholds(db: SQLiteDatabase): List<PrioritizedHousehold> {
        val list = mutableListOf<PrioritizedHousehold>()
        val query = """
            SELECT h.id, h.name, h.village, h.income_band, h.category,
                   pq.score, pq.reasons_json,
                   (SELECT last_visit_date FROM mothers m WHERE m.household_id = h.id ORDER BY m.last_visit_date DESC LIMIT 1) as last_visit,
                   (SELECT COUNT(*) FROM mothers m WHERE m.household_id = h.id) as mother_count,
                   (SELECT COUNT(*) FROM children c WHERE c.household_id = h.id) as child_count
            FROM priority_queue pq
            JOIN households h ON h.id = pq.household_id
            ORDER BY pq.score DESC
        """.trimIndent()

        val cursor = db.rawQuery(query, null)
        val listType = object : TypeToken<List<String>>() {}.type
        cursor.use {
            while (it.moveToNext()) {
                val score = it.getDouble(5)
                val tier = when {
                    score >= HIGH_THRESHOLD -> "HIGH"
                    score >= MEDIUM_THRESHOLD -> "MEDIUM"
                    else -> "LOW"
                }
                val reasonsRaw = it.getString(6) ?: "[]"
                val reasons: List<String> = try {
                    gson.fromJson(reasonsRaw, listType) ?: emptyList()
                } catch (e: Exception) {
                    emptyList()
                }

                list.add(
                    PrioritizedHousehold(
                        id = it.getString(0),
                        name = it.getString(1),
                        village = it.getString(2),
                        incomeBand = it.getString(3),
                        category = it.getString(4),
                        score = score,
                        urgencyTier = tier,
                        reasons = reasons,
                        lastVisitDate = it.getString(7),
                        motherCount = it.getInt(8),
                        childCount = it.getInt(9)
                    )
                )
            }
        }
        return list
    }
}
