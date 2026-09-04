package com.sahaya.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.sahaya.app.ui.screens.ChooseLanguageScreen
import com.sahaya.app.ui.screens.HouseholdDetailScreen
import com.sahaya.app.ui.screens.HouseholdListScreen
import com.sahaya.app.ui.screens.ProfileSetupScreen
import com.sahaya.app.ui.screens.VoiceAssistantSheet
import com.sahaya.app.ui.screens.WelcomeScreen
import com.sahaya.app.ui.theme.SahayaTheme

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    private val requestAudioPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            viewModel.toggleVoiceInput()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("sahaya_prefs", Context.MODE_PRIVATE)
        val initialOnboarded = prefs.getBoolean("onboarding_complete", false) // Fresh launch starts on Welcome screen

        setContent {
            SahayaTheme {
                val households by viewModel.households.collectAsState()
                val selectedDetails by viewModel.selectedHouseholdDetails.collectAsState()
                val isVoiceOpen by viewModel.isVoiceAssistantOpen.collectAsState()
                val contextHh by viewModel.contextHousehold.collectAsState()
                val turns by viewModel.conversationTurns.collectAsState()
                val isListening by viewModel.isListening.collectAsState()
                val isFollowUpCue by viewModel.isFollowUpCueActive.collectAsState()
                val activeLang by viewModel.activeLanguage.collectAsState()

                var isLanguageScreenOpen by remember { mutableStateOf(false) }
                var isOnboardingActive by remember { mutableStateOf(!initialOnboarded) }
                var onboardingStep by remember { mutableIntStateOf(0) } // 0: Welcome, 1: Profile Setup

                Box(modifier = Modifier.fillMaxSize()) {
                    when {
                        isLanguageScreenOpen -> {
                            ChooseLanguageScreen(
                                currentLanguage = activeLang,
                                onBack = { isLanguageScreenOpen = false },
                                onSelectLanguage = { lang ->
                                    viewModel.setLanguage(lang)
                                    isLanguageScreenOpen = false
                                }
                            )
                        }
                        isOnboardingActive && onboardingStep == 0 -> {
                            WelcomeScreen(
                                currentLanguage = activeLang,
                                onLanguageSelected = { lang -> viewModel.setLanguage(lang) },
                                onGetStarted = { onboardingStep = 1 }
                            )
                        }
                        isOnboardingActive && onboardingStep == 1 -> {
                            ProfileSetupScreen(
                                onBack = {
                                    if (prefs.getBoolean("onboarding_complete", false)) {
                                        isOnboardingActive = false
                                    } else {
                                        onboardingStep = 0
                                    }
                                },
                                onSaveAndContinue = { name, dist, vill ->
                                    viewModel.saveProfile(name, dist, vill)
                                    prefs.edit().putBoolean("onboarding_complete", true).apply()
                                    isOnboardingActive = false
                                },
                                onSkip = {
                                    prefs.edit().putBoolean("onboarding_complete", true).apply()
                                    isOnboardingActive = false
                                }
                            )
                        }
                        selectedDetails != null -> {
                            HouseholdDetailScreen(
                                details = selectedDetails,
                                activeLanguage = activeLang,
                                onBack = { viewModel.clearSelectedHousehold() },
                                onOpenVoiceWithContext = { id, name ->
                                    viewModel.openVoiceAssistant(id, name)
                                }
                            )
                        }
                        else -> {
                            HouseholdListScreen(
                                households = households,
                                activeLanguage = activeLang,
                                onHouseholdClick = { id -> viewModel.selectHousehold(id) },
                                onOpenVoiceAssistant = { viewModel.openVoiceAssistant() },
                                onOpenLanguageScreen = { isLanguageScreenOpen = true },
                                onOpenProfile = {
                                    isOnboardingActive = true
                                    onboardingStep = 1
                                },
                                onRefresh = { viewModel.loadHouseholds() }
                            )
                        }
                    }

                    // Multi-turn Voice Assistant Bottom Sheet
                    AnimatedVisibility(
                        visible = isVoiceOpen,
                        enter = slideInVertically(initialOffsetY = { it }),
                        exit = slideOutVertically(targetOffsetY = { it })
                    ) {
                        VoiceAssistantSheet(
                            conversationTurns = turns,
                            contextHouseholdName = contextHh?.second,
                            activeLanguage = activeLang,
                            isListening = isListening,
                            isFollowUpCueActive = isFollowUpCue,
                            onClose = { viewModel.closeVoiceAssistant() },
                            onResetConversation = { viewModel.resetConversation() },
                            onMicClick = { checkAudioPermissionAndListen() },
                            onSendQuery = { query -> viewModel.sendQuery(query) },
                            onSpeakText = { text -> viewModel.voiceManager.speak(text) }
                        )
                    }
                }
            }
        }
    }

    private fun checkAudioPermissionAndListen() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            viewModel.toggleVoiceInput()
        } else {
            requestAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }
}
