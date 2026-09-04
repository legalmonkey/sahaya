package com.sahaya.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sahaya.app.data.local.PrioritizedHousehold
import com.sahaya.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HouseholdListScreen(
    households: List<PrioritizedHousehold>,
    activeLanguage: String,
    onHouseholdClick: (String) -> Unit,
    onOpenVoiceAssistant: () -> Unit,
    onOpenLanguageScreen: () -> Unit,
    onOpenProfile: () -> Unit,
    onRefresh: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "सहया • Sahaya",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = TextPrimary
                        )
                        Text(
                            text = if (activeLanguage == "hi") "आशा फील्ड सहायक" else "ASHA Field Assistant",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                },
                actions = {
                    // Language Switcher Pill (matching Figma: हिं / EN)
                    Surface(
                        onClick = onOpenLanguageScreen,
                        shape = RoundedCornerShape(18.dp),
                        color = Color.White,
                        border = androidx.compose.foundation.BorderStroke(1.dp, WarmBorder),
                        modifier = Modifier.padding(end = 6.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                        ) {
                            Text(text = "🌐", fontSize = 12.sp)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = when (activeLanguage) {
                                    "hi" -> "हिं / EN"
                                    "ta" -> "த / EN"
                                    else -> "EN / हिं"
                                },
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = NavyBlue
                            )
                        }
                    }

                    IconButton(onClick = onOpenProfile) {
                        Icon(Icons.Default.AccountCircle, contentDescription = "Worker Profile", tint = NavyBlue)
                    }

                    IconButton(onClick = onRefresh) {
                        Icon(Icons.Default.FilterList, contentDescription = "Filter", tint = TextPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CreamBg)
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onOpenVoiceAssistant,
                containerColor = Terracotta,
                contentColor = Color.White,
                shape = CircleShape,
                modifier = Modifier
                    .size(62.dp)
                    .padding(bottom = 4.dp, end = 4.dp)
            ) {
                Icon(Icons.Default.Mic, contentDescription = "Voice Assistant", modifier = Modifier.size(32.dp))
            }
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(CreamBg)
                .padding(horizontal = 16.dp)
        ) {
            Spacer(modifier = Modifier.height(6.dp))

            // Subtitle: HOUSEHOLDS TO VISIT (6)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (activeLanguage == "hi") "भेंट हेतु परिवार (${households.size})" else "HOUSEHOLDS TO VISIT (${households.size})",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = TextPrimary,
                    letterSpacing = 0.5.sp
                )
            }

            // Household Cards List
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 80.dp)
            ) {
                items(households, key = { it.id }) { h ->
                    FigmaHouseholdCardItem(h = h, onClick = { onHouseholdClick(h.id) })
                }
            }
        }
    }
}

@Composable
fun FigmaHouseholdCardItem(h: PrioritizedHousehold, onClick: () -> Unit) {
    // Map score to Figma badge: CRITICAL, ATTENTION, ON TRACK
    val (badgeText, badgeBg, badgeTextColor, alertIconColor) = when (h.urgencyTier) {
        "HIGH" -> Quad("CRITICAL", BadgeCriticalBg, BadgeCriticalText, BadgeCriticalText)
        "MEDIUM" -> Quad("ATTENTION", BadgeAttentionBg, BadgeAttentionText, BadgeAttentionText)
        else -> Quad("ON TRACK", BadgeOnTrackBg, BadgeOnTrackText, BadgeOnTrackText)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = CardSurface),
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, WarmBorder),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = h.name,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(badgeBg)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = badgeText,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = badgeTextColor
                    )
                }
            }

            Spacer(modifier = Modifier.height(2.dp))

            // Village location tag
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.LocationOn,
                    contentDescription = null,
                    tint = Terracotta,
                    modifier = Modifier.size(13.dp)
                )
                Spacer(modifier = Modifier.width(3.dp))
                Text(
                    text = h.village,
                    fontSize = 12.sp,
                    color = TextSecondary,
                    fontWeight = FontWeight.Medium
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Primary reason / alert line matching Figma
            val primaryReason = h.reasons.firstOrNull() ?: "On track - next visit scheduled"
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = if (badgeText == "ON TRACK") "✓" else "!",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = alertIconColor,
                    modifier = Modifier
                        .size(18.dp)
                        .clip(CircleShape)
                        .background(badgeBg)
                        .wrapContentSize(Alignment.Center)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = primaryReason,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
            }
        }
    }
}

data class Quad<A, B, C, D>(val a: A, val b: B, val c: C, val d: D)
