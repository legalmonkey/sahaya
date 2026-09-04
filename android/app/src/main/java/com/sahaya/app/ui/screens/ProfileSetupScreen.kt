package com.sahaya.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
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
import com.sahaya.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileSetupScreen(
    onBack: () -> Unit,
    onSaveAndContinue: (name: String, district: String, village: String) -> Unit,
    onSkip: () -> Unit
) {
    var fullName by remember { mutableStateOf("Sunita Sharma") }
    var district by remember { mutableStateOf("Pipra, Supaul") }
    var village by remember { mutableStateOf("Pipra Tola 1") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Terracotta
                        )
                    }
                },
                actions = {
                    // Step 2 of 2 indicator matching Figma
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(end = 16.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .clip(CircleShape)
                                .background(WarmBorder)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .clip(CircleShape)
                                .background(Terracotta)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Step 2 of 2",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Terracotta
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CreamBg)
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Button(
                    onClick = { onSaveAndContinue(fullName, district, village) },
                    colors = ButtonDefaults.buttonColors(containerColor = Terracotta),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("सहेजें और जारी रखें", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                        Text("SAVE & CONTINUE", fontSize = 11.sp, fontWeight = FontWeight.Medium)
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                TextButton(onClick = onSkip) {
                    Text(
                        text = "Skip for now / बाद में भरें",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextSecondary
                    )
                }
            }
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(CreamBg)
                .padding(horizontal = 20.dp, vertical = 8.dp)
        ) {
            Text(
                text = "कार्यकर्ता प्रोफ़ाइल सेटअप",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Worker Profile Setup",
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Terracotta
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Provide your basic details to localize scheduling & immunization rules.",
                fontSize = 13.sp,
                color = TextSecondary,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Full Name Field
            Text(
                text = "Full Name / नाम",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(6.dp))
            OutlinedTextField(
                value = fullName,
                onValueChange = { fullName = it },
                leadingIcon = {
                    Icon(Icons.Default.Person, contentDescription = null, tint = NavyBlue)
                },
                placeholder = { Text("Enter your full name", color = TextMuted) },
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = CardSurface,
                    unfocusedContainerColor = CardSurface,
                    focusedBorderColor = Terracotta,
                    unfocusedBorderColor = WarmBorder
                ),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(18.dp))

            // Block & District Field
            Text(
                text = "Block & District / ब्लॉक और जिला",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(6.dp))
            OutlinedTextField(
                value = district,
                onValueChange = { district = it },
                leadingIcon = {
                    Icon(Icons.Default.LocationOn, contentDescription = null, tint = NavyBlue)
                },
                trailingIcon = {
                    Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, tint = TextSecondary)
                },
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = CardSurface,
                    unfocusedContainerColor = CardSurface,
                    focusedBorderColor = Terracotta,
                    unfocusedBorderColor = WarmBorder
                ),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(18.dp))

            // Assigned Village Field
            Text(
                text = "Assigned Village / आवंटित ग्राम",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(6.dp))
            OutlinedTextField(
                value = village,
                onValueChange = { village = it },
                leadingIcon = {
                    Icon(Icons.Default.Home, contentDescription = null, tint = NavyBlue)
                },
                trailingIcon = {
                    Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, tint = TextSecondary)
                },
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = CardSurface,
                    unfocusedContainerColor = CardSurface,
                    focusedBorderColor = Terracotta,
                    unfocusedBorderColor = WarmBorder
                ),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        }
    }
}
