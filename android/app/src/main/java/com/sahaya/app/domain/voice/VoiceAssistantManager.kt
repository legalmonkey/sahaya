package com.sahaya.app.domain.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import com.sahaya.app.data.local.ConversationTurn
import com.sahaya.app.data.retrieval.LocalRetriever
import java.util.Locale

class VoiceAssistantManager(
    private val context: Context,
    private val retriever: LocalRetriever
) : RecognitionListener, TextToSpeech.OnInitListener {

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false

    var activeLanguage: String = "hi" // "hi", "en", "ta"
    var isListening: Boolean = false
        private set

    var onListeningStateChanged: ((Boolean) -> Unit)? = null
    var onSpeechRecognized: ((String) -> Unit)? = null
    var onError: ((String) -> Unit)? = null
    var onFollowUpListeningCue: (() -> Unit)? = null

    val conversationBuffer = mutableListOf<ConversationTurn>()

    init {
        if (SpeechRecognizer.isRecognitionAvailable(context)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
                setRecognitionListener(this@VoiceAssistantManager)
            }
        }
        tts = TextToSpeech(context, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            ttsReady = true
            setLanguage(activeLanguage)
        }
    }

    fun setLanguage(lang: String) {
        activeLanguage = lang
        val locale = when (lang) {
            "ta" -> Locale("ta", "IN")
            "en" -> Locale.ENGLISH
            "mr" -> Locale("mr", "IN")
            else -> Locale("hi", "IN")
        }
        if (ttsReady) {
            tts?.language = locale
        }
    }

    fun startListening() {
        if (speechRecognizer == null) {
            onError?.invoke("Speech recognition is not available on this device.")
            return
        }
        val localeStr = when (activeLanguage) {
            "ta" -> "ta-IN"
            "en" -> "en-IN"
            "mr" -> "mr-IN"
            else -> "hi-IN"
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, localeStr)
            putExtra(RecognizerIntent.EXTRA_PROMPT, "सहया सुन रहा है...")
        }
        isListening = true
        onListeningStateChanged?.invoke(true)
        speechRecognizer?.startListening(intent)
    }

    fun stopListening() {
        isListening = false
        onListeningStateChanged?.invoke(false)
        speechRecognizer?.stopListening()
    }

    fun speak(text: String, onFinished: (() -> Unit)? = null) {
        if (ttsReady && text.isNotBlank()) {
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "sahaya_answer")
            // After answer finishes speaking, prompt follow-up listening
            onFollowUpListeningCue?.invoke()
        }
    }

    fun processQuery(
        query: String,
        householdContext: String? = null
    ): ConversationTurn {
        val previousTurns = conversationBuffer.takeLast(2).map { it.query to it.answer }
        val enrichedQuery = if (householdContext != null) "$query $householdContext" else query

        val results = retriever.searchWithConversation(enrichedQuery, previousTurns, topK = 3)
        if (results.isEmpty() || results[0].score <= 0.0) {
            val turn = ConversationTurn(
                query = query,
                answer = "आधिकारिक स्रोतों में इस प्रश्न के लिए पर्याप्त जानकारी नहीं मिली।",
                sourceChunks = emptyList(),
                confidence = 0.0
            )
            return turn
        }

        val topResult = results[0]
        val confidence = retriever.confidence(results)
        val sourceList = results.filter { it.score > 0.0 }.map { it.chunk }

        // Formulate protocol-grounded answer based on official source
        val answerText = topResult.chunk.text

        val turn = ConversationTurn(
            query = query,
            answer = answerText,
            sourceChunks = sourceList,
            confidence = confidence
        )

        conversationBuffer.add(turn)
        if (conversationBuffer.size > 2) {
            conversationBuffer.removeAt(0)
        }

        return turn
    }

    fun resetConversation() {
        conversationBuffer.clear()
        stopListening()
        tts?.stop()
    }

    fun destroy() {
        speechRecognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
    }

    // SpeechRecognizer Callbacks
    override fun onReadyForSpeech(params: Bundle?) {}
    override fun onBeginningOfSpeech() {}
    override fun onRmsChanged(rmsdB: Float) {}
    override fun onBufferReceived(buffer: ByteArray?) {}
    override fun onEndOfSpeech() {
        isListening = false
        onListeningStateChanged?.invoke(false)
    }

    override fun onError(error: Int) {
        isListening = false
        onListeningStateChanged?.invoke(false)
    }

    override fun onResults(results: Bundle?) {
        isListening = false
        onListeningStateChanged?.invoke(false)
        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        if (!matches.isNullOrEmpty()) {
            val text = matches[0]
            onSpeechRecognized?.invoke(text)
        }
    }

    override fun onPartialResults(partialResults: Bundle?) {}
    override fun onEvent(eventType: Int, params: Bundle?) {}
}
