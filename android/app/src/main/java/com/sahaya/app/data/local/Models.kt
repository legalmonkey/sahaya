package com.sahaya.app.data.local

data class Household(
    val id: String,
    val name: String,
    val village: String,
    val incomeBand: String? = null,
    val category: String? = null,
    val contactNotes: String? = null
)

data class Mother(
    val id: String,
    val householdId: String,
    val age: Int? = null,
    val lmpDate: String? = null,
    val ancVisitCount: Int = 0,
    val riskFlags: List<String> = emptyList(),
    val lastVisitDate: String? = null,
    val checkups: List<AncCheckup> = emptyList()
)

data class VaccineDose(
    val vaccine: String,
    val dateGiven: String? = null,
    val dueDate: String? = null
)

data class Child(
    val id: String,
    val householdId: String,
    val dob: String,
    val doseHistory: List<VaccineDose> = emptyList()
)

data class AncCheckup(
    val id: String,
    val motherId: String,
    val date: String,
    val bp: String? = null,
    val hbLevel: Double? = null,
    val dangerSigns: List<String> = emptyList(),
    val notes: String? = null
)

data class SchemeMatch(
    val householdId: String,
    val schemeName: String,
    val eligible: Boolean,
    val reason: String,
    val nextAction: String
)

data class PrioritizedHousehold(
    val id: String,
    val name: String,
    val village: String,
    val incomeBand: String?,
    val category: String?,
    val score: Double,
    val urgencyTier: String, // "HIGH", "MEDIUM", "LOW"
    val reasons: List<String>,
    val lastVisitDate: String?,
    val motherCount: Int,
    val childCount: Int
)

data class CorpusChunk(
    val id: String,
    val title: String,
    val authority: String,
    val source_url: String,
    val text: String
)

data class RetrievalResult(
    val chunk: CorpusChunk,
    val score: Double
)

data class ConversationTurn(
    val query: String,
    val answer: String,
    val sourceChunks: List<CorpusChunk> = emptyList(),
    val confidence: Double = 0.0
)
