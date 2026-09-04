package com.sahaya.app.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sahaya.app.data.local.ConversationTurn
import com.sahaya.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceAssistantSheet(
    conversationTurns: List<ConversationTurn>,
    contextHouseholdName: String?,
    activeLanguage: String,
    isListening: Boolean,
    isFollowUpCueActive: Boolean,
    onClose: () -> Unit,
    onResetConversation: () -> Unit,
    onMicClick: () -> Unit,
    onSendQuery: (String) -> Unit,
    onSpeakText: (String) -> Unit
) {
    var textInput by remember { mutableStateOf("") }

    // Pulsing animation for concentric rings
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseSize by infiniteTransition.animateFloat(
        initialValue = 110f,
        targetValue = 140f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseSize"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = if (conversationTurns.isEmpty()) "Voice Assistant" else "Sahaya Answer",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Terracotta)
                    }
                },
                actions = {
                    if (conversationTurns.isNotEmpty()) {
                        Button(
                            onClick = onResetConversation,
                            colors = ButtonDefaults.buttonColors(containerColor = Terracotta),
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                            modifier = Modifier.padding(end = 8.dp)
                        ) {
                            Text("Done", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CreamBg)
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(CreamBg)
        ) {
            // STATE 1: Empty state -> matching `voice-assistant-terracotta-blue`
            if (conversationTurns.isEmpty()) {
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(
                        text = "Ask a question सवाल पूछें...",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = TextPrimary,
                        textAlign = TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(36.dp))

                    // Concentric terracotta pulsing rings around mic
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier.size(170.dp)
                    ) {
                        // Outer Ring
                        Box(
                            modifier = Modifier
                                .size(pulseSize.dp)
                                .clip(CircleShape)
                                .background(Terracotta.copy(alpha = 0.12f))
                        )
                        // Middle Ring
                        Box(
                            modifier = Modifier
                                .size((pulseSize * 0.85f).dp)
                                .clip(CircleShape)
                                .background(Terracotta.copy(alpha = 0.22f))
                        )
                        // Inner Mic Button
                        IconButton(
                            onClick = onMicClick,
                            modifier = Modifier
                                .size(76.dp)
                                .clip(CircleShape)
                                .background(Terracotta)
                        ) {
                            Icon(
                                Icons.Default.Mic,
                                contentDescription = "Mic",
                                tint = Color.White,
                                modifier = Modifier.size(38.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(36.dp))

                    // Suggested prompt pill matching Figma
                    Surface(
                        onClick = { onSendQuery("Aarav ko agla vaccine kab lagna hai?") },
                        shape = RoundedCornerShape(20.dp),
                        color = Color.Transparent,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    ) {
                        Text(
                            text = "\"Aarav ko agla vaccine kab lagna hai?\"",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = NavyBlue,
                            textAlign = TextAlign.Center
                        )
                    }

                    Spacer(modifier = Modifier.height(30.dp))
                }

                // Bottom typing fallback
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(CreamBg)
                        .padding(horizontal = 20.dp, vertical = 14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Or type your question / या लिखकर पूछें",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = textInput,
                        onValueChange = { textInput = it },
                        placeholder = { Text("Search database directly...", fontSize = 13.sp, color = TextMuted) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = CardSurface,
                            unfocusedContainerColor = CardSurface,
                            focusedBorderColor = Terracotta,
                            unfocusedBorderColor = WarmBorder
                        )
                    )
                    if (textInput.isNotBlank()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = {
                                onSendQuery(textInput)
                                textInput = ""
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Terracotta),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Search / खोजें", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            } else {
                // STATE 2: AI Answer Screen -> matching `ai-answer-terracotta-blue`
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    contentPadding = PaddingValues(vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(conversationTurns) { turn ->
                        // User Bubble (Light blue pill, right-aligned)
                        Box(
                            modifier = Modifier.fillMaxWidth(),
                            contentAlignment = Alignment.CenterEnd
                        ) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(16.dp))
                                    .background(NavyBlueLight)
                                    .padding(horizontal = 14.dp, vertical = 10.dp)
                            ) {
                                Text(
                                    text = "\"${turn.query}\"",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = NavyBlue
                                )
                            }
                        }

                        // Sahaya Grounded Answer Card matching Figma
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = CardSurface),
                            shape = RoundedCornerShape(14.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, WarmBorder),
                            elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        tint = BadgeOnTrackText,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = "Penta-3 Overdue Alert",
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.ExtraBold,
                                        color = TextPrimary
                                    )
                                }

                                Spacer(modifier = Modifier.height(10.dp))
                                Text(
                                    text = turn.answer,
                                    fontSize = 13.sp,
                                    lineHeight = 20.sp,
                                    color = TextPrimary
                                )

                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "📄 SOURCE: UIP Schedule, MoHFW Guidelines 2025",
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextMuted
                                )
                            }
                        }
                    }
                }

                // Bottom bar matching Figma: "● Still listening... Ask follow-up" + Terracotta Mic
                Surface(
                    color = CardSurface,
                    shadowElevation = 4.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(BadgeCriticalText)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Still listening... Ask follow-up",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = NavyBlue
                            )
                        }

                        IconButton(
                            onClick = onMicClick,
                            modifier = Modifier
                                .size(46.dp)
                                .clip(CircleShape)
                                .background(Terracotta)
                        ) {
                            Icon(
                                Icons.Default.Mic,
                                contentDescription = "Mic",
                                tint = Color.White,
                                modifier = Modifier.size(24.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}
