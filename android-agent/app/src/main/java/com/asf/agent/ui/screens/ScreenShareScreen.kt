package com.asf.agent.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.asf.agent.ui.theme.*

@Composable
fun ScreenShareScreen(
    isStreaming: Boolean,
    onStartRequested: () -> Unit,
    onStopRequested: () -> Unit,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "SCREEN SHARE CENTER",
            color = AccentBlue,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
        Text(
            text = "User-approved screen streaming to authenticated ASF operator dashboard.",
            color = TextSecondary,
            fontSize = 13.sp
        )

        Divider(color = BorderSubtle)

        // Session status card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "ACTIVE SESSION INDICATOR",
                    color = TextSecondary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val statusColor = if (isStreaming) AccentRose else TextMuted
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(statusColor)
                    )
                    Text(
                        text = if (isStreaming) "STREAMING ACTIVE" else "STREAM IDLE",
                        color = if (isStreaming) AccentRose else TextSecondary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Text(
                    text = if (isStreaming)
                        "Android MediaProjection virtual display is capturing 720p frames. An ongoing notification is visible in your notification tray."
                    else
                        "No screen capture is running. Tap Start below to launch system consent dialog.",
                    color = TextSecondary,
                    fontSize = 12.sp
                )
            }
        }

        // Security Notice Box
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(DarkSurfaceElevated)
                .border(1.dp, BorderSubtle, RoundedCornerShape(6.dp))
                .padding(12.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "UN-BYPASSABLE OS CONSENT",
                    color = AccentAmber,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Screen capture cannot be started covertly. Android enforces an interactive system confirmation dialog and displays a persistent status bar icon throughout the session.",
                    color = TextSecondary,
                    fontSize = 11.sp
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (!isStreaming) {
                Button(
                    onClick = onStartRequested,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(text = "REQUEST SCREEN CAPTURE CONSENT", color = DarkBackground, fontWeight = FontWeight.Bold)
                }
            } else {
                Button(
                    onClick = onStopRequested,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentRose),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(text = "STOP SCREEN SHARING", color = TextPrimary, fontWeight = FontWeight.Bold)
                }
            }

            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(6.dp)
            ) {
                Text(text = "BACK TO HOME", color = TextSecondary)
            }
        }
    }
}
