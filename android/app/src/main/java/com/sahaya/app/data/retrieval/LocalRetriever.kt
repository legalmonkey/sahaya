package com.sahaya.app.data.retrieval

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.sahaya.app.data.local.CorpusChunk
import com.sahaya.app.data.local.RetrievalResult
import java.io.InputStream
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

class LocalRetriever(rawJson: String) {

    private val chunks: List<CorpusChunk>
    private val idf: Map<String, Double>
    private val vectors: List<Map<String, Double>>

    init {
        val listType = object : TypeToken<List<CorpusChunk>>() {}.type
        chunks = Gson().fromJson(rawJson, listType) ?: emptyList()
        if (chunks.isEmpty()) {
            throw IllegalArgumentException("The local corpus cannot be empty.")
        }

        val documents = chunks.map { tokenize("${it.title} ${it.text}") }
        val docFrequency = mutableMapOf<String, Int>()
        for (doc in documents) {
            val uniqueTokens = doc.toSet()
            for (token in uniqueTokens) {
                docFrequency[token] = (docFrequency[token] ?: 0) + 1
            }
        }

        val total = documents.size.toDouble()
        idf = docFrequency.mapValues { (_, freq) ->
            ln((total + 1.0) / (freq + 1.0)) + 1.0
        }

        vectors = documents.map { vectorize(it) }
    }

    companion object {
        private val TOKEN_REGEX = Regex("""\w+""", RegexOption.IGNORE_CASE)

        fun fromAssets(context: Context, assetName: String = "corpus.json"): LocalRetriever {
            val json = context.assets.open(assetName).bufferedReader().use { it.readText() }
            return LocalRetriever(json)
        }

        fun fromInputStream(stream: InputStream): LocalRetriever {
            val json = stream.bufferedReader().use { it.readText() }
            return LocalRetriever(json)
        }

        fun tokenize(text: String): List<String> {
            return TOKEN_REGEX.findAll(text.lowercase()).map { it.value }.toList()
        }
    }

    private fun vectorize(tokens: List<String>): Map<String, Double> {
        val counts = mutableMapOf<String, Int>()
        for (t in tokens) {
            counts[t] = (counts[t] ?: 0) + 1
        }
        val weighted = mutableMapOf<String, Double>()
        var sumSq = 0.0
        for ((token, count) in counts) {
            val weight = count * (idf[token] ?: 0.0)
            if (weight > 0) {
                weighted[token] = weight
                sumSq += weight * weight
            }
        }
        val norm = sqrt(sumSq)
        return if (norm > 0) {
            weighted.mapValues { (_, v) -> v / norm }
        } else {
            emptyMap()
        }
    }

    private fun cosine(left: Map<String, Double>, right: Map<String, Double>): Double {
        var dot = 0.0
        for ((k, v) in left) {
            val r = right[k]
            if (r != null) {
                dot += v * r
            }
        }
        return dot
    }

    fun search(query: String, topK: Int = 3): List<RetrievalResult> {
        val trimmed = query.trim()
        if (trimmed.isEmpty()) {
            throw IllegalArgumentException("A question is required.")
        }
        val qVec = vectorize(tokenize(trimmed))
        val scored = chunks.mapIndexed { idx, chunk ->
            RetrievalResult(chunk, cosine(qVec, vectors[idx]))
        }
        return scored.sortedByDescending { it.score }.take(topK)
    }

    fun searchWithConversation(query: String, previousTurns: List<Pair<String, String>>, topK: Int = 3): List<RetrievalResult> {
        val contextTerms = previousTurns.takeLast(2).map { it.first }.filter { it.isNotBlank() }
        val foldedQuery = if (contextTerms.isNotEmpty()) {
            "${contextTerms.joinToString(" ")} $query"
        } else {
            query
        }
        return search(foldedQuery, topK)
    }

    fun confidence(results: List<RetrievalResult>): Double {
        if (results.isEmpty() || results[0].score <= 0.0) return 0.0
        val first = results[0].score
        val second = if (results.size > 1) results[1].score else 0.0
        val derived = min(1.0, first * 0.75 + max(0.0, first - second) * 0.25)
        return (derived * 1000.0).toInt() / 1000.0
    }
}
