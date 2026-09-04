package com.sahaya.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = Terracotta,
    onPrimary = Color.White,
    primaryContainer = TerracottaLight,
    onPrimaryContainer = TerracottaDark,
    secondary = NavyBlue,
    onSecondary = Color.White,
    secondaryContainer = NavyBlueLight,
    onSecondaryContainer = NavyBlueDark,
    background = CreamBg,
    onBackground = TextPrimary,
    surface = CardSurface,
    onSurface = TextPrimary,
    surfaceVariant = CreamBg,
    onSurfaceVariant = TextSecondary,
    outline = WarmBorder
)

@Composable
fun SahayaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content = content
    )
}
