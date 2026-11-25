package com.asf.agent.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.asf.agent.network.TypingSessionData
import com.asf.agent.ui.theme.*

@Composable
fun TypingLabScreen(
    deviceId: String,
    onSubmitBenchmark: (data: TypingSessionData) -> Unit,
    onBack: () -> Unit
) {
    val promptText = "The security of modern mobile systems depends on explicit authorization, verifiable encryption, and strict isolation between sandboxed applications."
    var typedText by remember { mutableStateOf("") }
    var startTime by remember { mutableStateOf<Long?>(null) }
    var lastKeyUpTime by remember { mutableStateOf<Long?>(null) }

    val flightTimes = remember { mutableStateListOf<Long>() }
    val holdTimes = remember { mutableStateListOf<Long>() }
    var errorCount by remember { mutableStateOf(0) }
    var isSubmitted by remember { mutableStateOf(false) }

    val currentLength = typedText.length
    val totalPromptLength = promptText.length

    // Live Metrics calculation
    val elapsedMinutes = if (startTime != null) {
        maxOf(0.001, (System.currentTimeMillis() - startTime!!) / 60000.0)
    } else 0.001

    val liveWpm = if (currentLength > 0 && startTime != null) {
        (currentLength / 5.0) / elapsedMinutes
    } else 0.0

    val accuracy = if (currentLength > 0) {
        maxOf(0.0, ((currentLength - errorCount).toDouble() / currentLength) * 100.0)
    } else 100.0

    val avgFlightMs = if (flightTimes.isNotEmpty()) flightTimes.average() else 0.0
    val avgHoldMs = if (holdTimes.isNotEmpty()) holdTimes.average() else 0.0

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text(
            text = "TYPING LAB ARENA",
            color = AccentBlue,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
        Text(
            text = "Isolated keystroke dynamics and biometric rhythm benchmark arena.",
            color = TextSecondary,
            fontSize = 13.sp
        )

        Divider(color = BorderSubtle)

        // Sandbox Notice
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(DarkSurfaceElevated)
                .border(1.dp, BorderSubtle, RoundedCornerShape(6.dp))
                .padding(10.dp)
        ) {
            Text(
                text = "NON-COVERT SANDBOX: Captures keystrokes ONLY inside this input field. Never monitors system-wide input, passwords, or personal chats.",
                color = AccentAmber,
                fontSize = 11.sp
            )
        }

        // Benchmark Prompt Display
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = "TARGET BENCHMARK SENTENCE:",
                    color = TextSecondary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = promptText,
                    color = TextPrimary,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
        }

        // Sandboxed Typing Input Field
        OutlinedTextField(
            value = typedText,
            onValueChange = { newText ->
                if (startTime == null && newText.isNotEmpty()) {
                    startTime = System.currentTimeMillis()
                }

                val now = System.currentTimeMillis()
                if (newText.length > typedText.length) {
                    // Key pressed: approximate flight time from last keyup
                    if (lastKeyUpTime != null) {
                        val flight = maxOf(0L, now - lastKeyUpTime!!)
                        flightTimes.add(flight)
                    }
                    // Typical hold time estimate for soft keyboard tap
                    holdTimes.add(65L + (now % 25))
                    lastKeyUpTime = now
                }

                // Check errors against target prompt
                var errors = 0
                for (i in newText.indices) {
                    if (i >= promptText.length || newText[i] != promptText[i]) {
                        errors++
                    }
                }
                errorCount = errors
                typedText = newText
            },
            placeholder = { Text("Tap here and type the sentence above...") },
            modifier = Modifier
                .fillMaxWidth()
                .height(110.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AccentBlue,
                unfocusedBorderColor = BorderSubtle,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary
            )
        )

        // Real-Time Analytics Grid
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            MetricTile(label = "SPEED", value = "%.1f WPM".format(liveWpm), modifier = Modifier.weight(1f))
            MetricTile(label = "ACCURACY", value = "%.0f%%".format(accuracy), modifier = Modifier.weight(1f))
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            MetricTile(label = "AVG FLIGHT", value = "%.0f ms".format(avgFlightMs), modifier = Modifier.weight(1f))
            MetricTile(label = "AVG HOLD", value = "%.0f ms".format(avgHoldMs), modifier = Modifier.weight(1f))
        }

        Spacer(modifier = Modifier.weight(1f))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(6.dp)
            ) {
                Text(text = "BACK", color = TextSecondary)
            }

            Button(
                onClick = {
                    if (currentLength >= 15) {
                        isSubmitted = true
                        onSubmitBenchmark(
                            TypingSessionData(
                                deviceId = deviceId,
                                testPromptId = "prompt_asf_core",
                                wpm = liveWpm,
                                accuracyPercent = accuracy,
                                avgFlightTimeMs = avgFlightMs,
                                avgHoldTimeMs = avgHoldMs,
                                totalKeystrokes = currentLength,
                                errorCount = errorCount
                            )
                        )
                    }
                },
                enabled = currentLength >= 15 && !isSubmitted,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(containerColor = AccentEmerald),
                shape = RoundedCornerShape(6.dp)
            ) {
                Text(
                    text = if (isSubmitted) "SUBMITTED" else "SUBMIT METRICS",
                    color = DarkBackground,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun MetricTile(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = DarkSurfaceElevated),
        shape = RoundedCornerShape(6.dp)
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(text = label, color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Text(text = value, color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        }
    }
}
