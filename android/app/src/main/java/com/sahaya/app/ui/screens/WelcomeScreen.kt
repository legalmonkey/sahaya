package com.sahaya.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sahaya.app.ui.theme.*

@Composable
fun WelcomeScreen(
    currentLanguage: String,
    onLanguageSelected: (String) -> Unit,
    onGetStarted: () -> Unit
) {
    var selectedLang by remember { mutableStateOf(currentLanguage) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(CreamBg)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(20.dp),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Spacer(modifier = Modifier.height(10.dp))

            // Illustrated Banner matching Figma welcome card
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(190.dp)
                    .clip(RoundedCornerShape(20.dp))
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                Color(0xFFE8D5C4),
                                Color(0xFFF3E7DC),
                                Color(0xFFDFBA9E)
                            )
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Box(
                        modifier = Modifier
                            .size(70.dp)
                            .clip(CircleShape)
                            .background(Color.White.copy(alpha = 0.85f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(text = "👩‍⚕️", fontSize = 36.sp)
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "स्वस्थ माँ, खुश बच्चा",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = NavyBlue
                    )
                    Text(
                        text = "Healthy Mother, Happy Child",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(26.dp))

            // Headline
            Text(
                text = "सहाय में आपका स्वागत है",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Welcome to Sahaya",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Terracotta
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Empowering ASHA workers with reliable, offline-first digital tools for maternal and child care.",
                fontSize = 14.sp,
                color = TextSecondary,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(28.dp))

            // Choose Language header
            Text(
                text = "CHOOSE LANGUAGE / भाषा चुनें",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = TextSecondary,
                letterSpacing = 0.5.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Language Cards side-by-side
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Hindi Card
                val isHindi = selectedLang == "hi"
                Card(
                    modifier = Modifier
                        .weight(1f)
                        .clickable {
                            selectedLang = "hi"
                            onLanguageSelected("hi")
                        },
                    colors = CardDefaults.cardColors(containerColor = CardSurface),
                    shape = RoundedCornerShape(14.dp),
                    border = androidx.compose.foundation.BorderStroke(
                        if (isHindi) 2.dp else 1.dp,
                        if (isHindi) Terracotta else WarmBorder
                    ),
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
                            verticalAlignment = Alignment.Top
                        ) {
                            Text(
                                text = "अ",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Terracotta
                            )
                            if (isHindi) {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .background(Terracotta),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        Icons.Default.Check,
                                        contentDescription = null,
                                        tint = Color.White,
                                        modifier = Modifier.size(14.dp)
                                    )
                                }
                            } else {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .border(1.5.dp, WarmBorder, CircleShape)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "हिन्दी",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Text(
                            text = "Hindi",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                }

                // English Card
                val isEn = selectedLang == "en"
                Card(
                    modifier = Modifier
                        .weight(1f)
                        .clickable {
                            selectedLang = "en"
                            onLanguageSelected("en")
                        },
                    colors = CardDefaults.cardColors(containerColor = CardSurface),
                    shape = RoundedCornerShape(14.dp),
                    border = androidx.compose.foundation.BorderStroke(
                        if (isEn) 2.dp else 1.dp,
                        if (isEn) Terracotta else WarmBorder
                    ),
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
                            verticalAlignment = Alignment.Top
                        ) {
                            Text(
                                text = "A",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = NavyBlue
                            )
                            if (isEn) {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .background(Terracotta),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        Icons.Default.Check,
                                        contentDescription = null,
                                        tint = Color.White,
                                        modifier = Modifier.size(14.dp)
                                    )
                                }
                            } else {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .border(1.5.dp, WarmBorder, CircleShape)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "English",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Text(
                            text = "English",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                }
            }
        }

        // Bottom CTA button
        Button(
            onClick = onGetStarted,
            colors = ButtonDefaults.buttonColors(containerColor = Terracotta),
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(54.dp)
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("शुरू करें", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text("GET STARTED", fontSize = 11.sp, fontWeight = FontWeight.Medium)
            }
        }
    }
}
