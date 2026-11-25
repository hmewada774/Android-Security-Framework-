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
import com.asf.agent.network.ConnectionStatus
import com.asf.agent.ui.theme.*

@Composable
fun HomeScreen(
    isPaired: Boolean,
    deviceId: String,
    deviceModel: String,
    osVersion: String,
    backendUrl: String,
    connectionStatus: ConnectionStatus,
    onNavigateToPairing: () -> Unit,
    onNavigateToScreenShare: () -> Unit,
    onNavigateToTypingLab: () -> Unit,
    onSendTelemetry: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // App Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "ASF AGENT",
                    color = AccentBlue,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace
                )
                Text(
                    text = "Android Security Framework",
                    color = TextSecondary,
                    fontSize = 12.sp
                )
            }

            // Connection Badge
            val (badgeText, badgeColor) = when (connectionStatus) {
                ConnectionStatus.CONNECTED -> "ONLINE" to AccentEmerald
                ConnectionStatus.CONNECTING -> "CONNECTING" to AccentAmber
                ConnectionStatus.REVOKED -> "REVOKED" to AccentRose
                ConnectionStatus.ERROR -> "ERROR" to AccentRose
                ConnectionStatus.DISCONNECTED -> "OFFLINE" to TextMuted
            }

            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(badgeColor.copy(alpha = 0.2f))
                    .border(1.dp, badgeColor, RoundedCornerShape(4.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    text = badgeText,
                    color = badgeColor,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        Divider(color = BorderSubtle)

        // Device Status Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "DEVICE CREDENTIALS",
                    color = TextSecondary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Device ID: $deviceId",
                    color = TextPrimary,
                    fontSize = 13.sp,
                    fontFamily = FontFamily.Monospace
                )
                Text(
                    text = "Hardware: $deviceModel",
                    color = TextSecondary,
                    fontSize = 12.sp
                )
                Text(
                    text = "OS: $osVersion",
                    color = TextSecondary,
                    fontSize = 12.sp
                )
                Text(
                    text = "Server: $backendUrl",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace
                )

                Spacer(modifier = Modifier.height(12.dp))

                if (isPaired) {
                    Text(
                        text = "STATUS: PAIRED & AUTHENTICATED",
                        color = AccentEmerald,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                } else {
                    Text(
                        text = "STATUS: UNPAIRED",
                        color = AccentAmber,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Action Buttons
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (!isPaired || connectionStatus == ConnectionStatus.REVOKED) {
                Button(
                    onClick = onNavigateToPairing,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(text = "PAIR WITH CONTROLLER PIN", color = DarkBackground, fontWeight = FontWeight.Bold)
                }
            } else {
                Button(
                    onClick = onNavigateToScreenShare,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(text = "SCREEN SHARE CENTER", color = DarkBackground, fontWeight = FontWeight.Bold)
                }

                Button(
                    onClick = onNavigateToTypingLab,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(text = "TYPING LAB BENCHMARK", color = TextPrimary)
                }

                OutlinedButton(
                    onClick = onSendTelemetry,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = AccentEmerald)
                ) {
                    Text(text = "POST TELEMETRY HEARTBEAT")
                }

                OutlinedButton(
                    onClick = onNavigateToPairing,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = TextSecondary)
                ) {
                    Text(text = "RE-CONFIGURE / RE-PAIR")
                }
            }
        }
    }
}
