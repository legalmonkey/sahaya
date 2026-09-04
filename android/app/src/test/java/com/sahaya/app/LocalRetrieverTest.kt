package com.sahaya.app

import com.sahaya.app.data.retrieval.LocalRetriever
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File

class LocalRetrieverTest {

    private lateinit var retriever: LocalRetriever

    @Before
    fun setUp() {
        val corpusFile = File("src/main/assets/corpus.json")
        val json = if (corpusFile.exists()) {
            corpusFile.readText()
        } else {
            File("../../data/corpus.json").readText()
        }
        retriever = LocalRetriever(json)
    }

    @Test
    fun testRetrievesOpvSchedule() {
        val results = retriever.search("When are oral polio vaccine doses due?")
        assertTrue(results.isNotEmpty())
        assertEquals("mohfw-nis-opv-002", results[0].chunk.id)
    }

    @Test
    fun testRetrievesHepatitisBirthDose() {
        val results = retriever.search("How soon after an institutional delivery is hepatitis B given?")
        assertTrue(results.isNotEmpty())
        assertEquals("mohfw-nis-hepb-003", results[0].chunk.id)
    }

    @Test
    fun testRetrievesPmsmaFixedDay() {
        val results = retriever.search("On which day does PMSMA provide antenatal care?")
        assertTrue(results.isNotEmpty())
        assertEquals("nhm-pmsma-anc-002", results[0].chunk.id)
    }

    @Test
    fun testConfidenceIsDerived() {
        val strong = retriever.confidence(retriever.search("OPV polio booster 16 24 months"))
        val weak = retriever.confidence(retriever.search("unrelated agricultural rainfall forecast"))
        assertTrue(strong > weak)
    }

    @Test
    fun testMultiTurnFollowupRetrievalFolding() {
        val priorTurns = listOf("When are oral polio vaccine doses due?" to "OPV is scheduled at birth, 6, 10, and 14 weeks.")
        val followup = "what about the booster dose then?"
        val results = retriever.searchWithConversation(followup, priorTurns)
        assertTrue(results.isNotEmpty())
        assertEquals("mohfw-nis-opv-002", results[0].chunk.id)
    }
}
