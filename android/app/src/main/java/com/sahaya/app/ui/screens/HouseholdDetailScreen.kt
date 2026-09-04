package com.sahaya.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sahaya.app.data.local.*
import com.sahaya.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HouseholdDetailScreen(
    details: Map<String, Any?>?,
    activeLanguage: String,
    onBack: () -> Unit,
    onOpenVoiceWithContext: (householdId: String, householdName: String) -> Unit
) {
    val household = details?.get("household") as? Household
    @Suppress("UNCHECKED_CAST")
    val mothers = details?.get("mothers") as? List<Mother> ?: emptyList()
    @Suppress("UNCHECKED_CAST")
    val children = details?.get("children") as? List<Child> ?: emptyList()
    @Suppress("UNCHECKED_CAST")
    val schemes = details?.get("schemes") as? List<SchemeMatch> ?: emptyList()

    var isImmunoExpanded by remember { mutableStateOf(true) }
    var isPregnancyExpanded by remember { mutableStateOf(false) }
    var isSchemesExpanded by remember { mutableStateOf(false) }
    var isDoseAdministered by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = household?.name ?: "Meena Devi's Family",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Text(
                            text = "${household?.village ?: "Pipra Village"} • ${household?.contactNotes ?: "Household ID: 409"}",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Terracotta)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CreamBg)
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    if (household != null) {
                        onOpenVoiceWithContext(household.id, household.name)
                    }
                },
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
        if (household == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Terracotta)
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(CreamBg)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Module 1: Immunization / टीकाकरण (Expanded with Terracotta highlighted border)
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.5.dp, TerracottaBorder),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { isImmunoExpanded = !isImmunoExpanded },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(NavyBlueLight),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("💉", fontSize = 16.sp)
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "Immunization / टीकाकरण",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = if (isDoseAdministered) "All doses given" else "1 Dose Overdue",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isDoseAdministered) BadgeOnTrackText else BadgeCriticalText
                                )
                            }
                        }
                        Icon(
                            if (isImmunoExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            tint = TextSecondary
                        )
                    }

                    if (isImmunoExpanded) {
                        Spacer(modifier = Modifier.height(12.dp))
                        HorizontalDivider(color = WarmBorder)
                        Spacer(modifier = Modifier.height(10.dp))

                        // Child details block
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Child: Aarav (14 Months)",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(if (isDoseAdministered) BadgeOnTrackBg else BadgeCriticalBg)
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = if (isDoseAdministered) "COMPLETED" else "OVERDUE",
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isDoseAdministered) BadgeOnTrackText else BadgeCriticalText
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = if (isDoseAdministered)
                                "Pentavalent-3 vaccine administered and recorded successfully."
                            else
                                "Pentavalent-3 vaccine scheduled for 12 Jan 2026. Missed during pipra camp. Requires immediate door-to-door visit and counseling.",
                            fontSize = 13.sp,
                            color = TextSecondary,
                            lineHeight = 18.sp
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // Action Button matching Figma (Navy Blue #1F3A52)
                        Button(
                            onClick = { isDoseAdministered = !isDoseAdministered },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isDoseAdministered) Color(0xFF334155) else NavyBlue
                            ),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Text(
                                text = if (isDoseAdministered) "✓ Dose Recorded / दर्ज किया गया" else "Mark Administered / टीका लगाया गया",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "📄 SOURCE: UIP SCHEDULE, PENTA-3",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextMuted
                        )
                    }
                }
            }

            // Module 2: Pregnancy Risk / गर्भावस्था (Collapsible Accordion)
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, WarmBorder),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { isPregnancyExpanded = !isPregnancyExpanded },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(NavyBlueLight),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("💙", fontSize = 16.sp)
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "Pregnancy Risk / गर्भावस्था",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "High Risk — Anemia detected (Hb 9.5)",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = BadgeAttentionText
                                )
                            }
                        }
                        Icon(
                            if (isPregnancyExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            tint = TextSecondary
                        )
                    }

                    if (isPregnancyExpanded) {
                        Spacer(modifier = Modifier.height(10.dp))
                        HorizontalDivider(color = WarmBorder)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Blood Pressure: 120/80 mmHg (Normal)", fontSize = 13.sp, color = TextPrimary)
                        Text("Hemoglobin: 9.5 g/dL (Mild to Moderate Anemia)", fontSize = 13.sp, color = BadgeAttentionText, fontWeight = FontWeight.SemiBold)
                        Text("Recommended Action: Distribute IFA tablets (100 days regimen) and schedule dietary counseling.", fontSize = 12.sp, color = TextSecondary)
                    }
                }
            }

            // Module 3: Govt Schemes / सरकारी योजनाएं (Collapsible Accordion)
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, WarmBorder),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { isSchemesExpanded = !isSchemesExpanded },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(NavyBlueLight),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("🛡️", fontSize = 16.sp)
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "Govt Schemes / सरकारी योजनाएं",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "2 Schemes Eligible (PMMVY, JSY)",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = NavyBlue
                                )
                            }
                        }
                        Icon(
                            if (isSchemesExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            tint = TextSecondary
                        )
                    }

                    if (isSchemesExpanded) {
                        Spacer(modifier = Modifier.height(10.dp))
                        HorizontalDivider(color = WarmBorder)
                        Spacer(modifier = Modifier.height(8.dp))

                        Text("1. PMMVY (Pradhan Mantri Matru Vandana Yojana)", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Text("Benefit: ₹5,000 in direct benefit transfer for first living child.", fontSize = 12.sp, color = TextSecondary)
                        Spacer(modifier = Modifier.height(6.dp))

                        Text("2. JSY (Janani Suraksha Yojana)", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        Text("Benefit: Cash assistance of ₹1,400 for institutional delivery.", fontSize = 12.sp, color = TextSecondary)
                    }
                }
            }

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}
