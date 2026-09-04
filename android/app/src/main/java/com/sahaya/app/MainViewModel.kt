package com.sahaya.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sahaya.app.data.local.ConversationTurn
import com.sahaya.app.data.local.PrioritizedHousehold
import com.sahaya.app.data.local.SahayaDbHelper
import com.sahaya.app.data.retrieval.LocalRetriever
import com.sahaya.app.domain.prioritization.PrioritizationEngine
import com.sahaya.app.domain.voice.VoiceAssistantManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val dbHelper = SahayaDbHelper(application)
    private val prioritizationEngine = PrioritizationEngine()
    private val retriever = LocalRetriever.fromAssets(application, "corpus.json")
    val voiceManager = VoiceAssistantManager(application, retriever)

    private val _households = MutableStateFlow<List<PrioritizedHousehold>>(emptyList())
    val households: StateFlow<List<PrioritizedHousehold>> = _households.asStateFlow()

    private val _selectedHouseholdDetails = MutableStateFlow<Map<String, Any?>?>(null)
    val selectedHouseholdDetails: StateFlow<Map<String, Any?>?> = _selectedHouseholdDetails.asStateFlow()

    private val _isVoiceAssistantOpen = MutableStateFlow(false)
    val isVoiceAssistantOpen: StateFlow<Boolean> = _isVoiceAssistantOpen.asStateFlow()

    private val _contextHousehold = MutableStateFlow<Pair<String, String>?>(null) // (id, name)
    val contextHousehold: StateFlow<Pair<String, String>?> = _contextHousehold.asStateFlow()

    private val _conversationTurns = MutableStateFlow<List<ConversationTurn>>(emptyList())
    val conversationTurns: StateFlow<List<ConversationTurn>> = _conversationTurns.asStateFlow()

    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

    private val _isFollowUpCueActive = MutableStateFlow(false)
    val isFollowUpCueActive: StateFlow<Boolean> = _isFollowUpCueActive.asStateFlow()

    private val _activeLanguage = MutableStateFlow("hi")
    val activeLanguage: StateFlow<String> = _activeLanguage.asStateFlow()

    init {
        voiceManager.onListeningStateChanged = { listening ->
            _isListening.value = listening
            if (listening) {
                _isFollowUpCueActive.value = false
            }
        }

        voiceManager.onSpeechRecognized = { spokenText ->
            sendQuery(spokenText)
        }

        voiceManager.onFollowUpListeningCue = {
            viewModelScope.launch {
                _isFollowUpCueActive.value = true
                delay(6000)
                _isFollowUpCueActive.value = false
            }
        }

        loadHouseholds()
    }

    fun loadHouseholds() {
        viewModelScope.launch(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            prioritizationEngine.refreshPriorityQueue(db)
            val list = prioritizationEngine.getPrioritizedHouseholds(db)
            _households.value = list
        }
    }

    fun selectHousehold(id: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val details = dbHelper.getHouseholdDetails(id)
            _selectedHouseholdDetails.value = details
        }
    }

    fun clearSelectedHousehold() {
        _selectedHouseholdDetails.value = null
    }

    fun openVoiceAssistant(householdId: String? = null, householdName: String? = null) {
        if (householdId != null && householdName != null) {
            _contextHousehold.value = householdId to householdName
        } else {
            _contextHousehold.value = null
        }
        _isVoiceAssistantOpen.value = true
    }

    fun closeVoiceAssistant() {
        _isVoiceAssistantOpen.value = false
        voiceManager.stopListening()
        _isFollowUpCueActive.value = false
    }

    fun setLanguage(lang: String) {
        _activeLanguage.value = lang
        voiceManager.setLanguage(lang)
    }

    private val _workerProfile = MutableStateFlow(Triple("Sunita Sharma", "Pipra, Supaul", "Pipra Tola 1"))
    val workerProfile: StateFlow<Triple<String, String, String>> = _workerProfile.asStateFlow()

    fun saveProfile(name: String, district: String, village: String) {
        _workerProfile.value = Triple(name, district, village)
    }

    fun toggleLanguage() {
        val next = when (_activeLanguage.value) {
            "hi" -> "en"
            "en" -> "ta"
            else -> "hi"
        }
        setLanguage(next)
    }

    fun toggleVoiceInput() {
        if (_isListening.value) {
            voiceManager.stopListening()
        } else {
            voiceManager.startListening()
        }
    }

    fun sendQuery(query: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val ctxHh = _contextHousehold.value
            val contextSummary = if (ctxHh != null) {
                val evaluated = prioritizationEngine.evaluateHousehold(ctxHh.first, dbHelper.readableDatabase)
                evaluated?.reasons?.take(2)?.joinToString(" ")
            } else null

            val turn = voiceManager.processQuery(query, contextSummary)
            _conversationTurns.value = voiceManager.conversationBuffer.toList()

            // Speak answer aloud
            voiceManager.speak(turn.answer)
        }
    }

    fun resetConversation() {
        voiceManager.resetConversation()
        _conversationTurns.value = emptyList()
        _isFollowUpCueActive.value = false
    }

    override fun onCleared() {
        super.onCleared()
        voiceManager.destroy()
        dbHelper.close()
    }
}
