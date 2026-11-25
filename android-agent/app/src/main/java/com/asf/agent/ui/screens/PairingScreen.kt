package com.asf.agent.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.asf.agent.ui.theme.*

@Composable
fun PairingScreen(
    currentBackendUrl: String,
    onClaimPairing: (pin: String, backendUrl: String, deviceName: String) -> Unit,
    onCancel: () -> Unit
) {
    var pin by remember { mutableStateOf("") }
    var backendUrl by remember { mutableStateOf(currentBackendUrl) }
    var deviceName by remember { mutableStateOf("Pixel / Android Test Device") }
    var isSubmitting by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "DEVICE PAIRING",
            color = AccentBlue,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
        Text(
            text = "Enter the one-time 6-digit PIN generated on the ASF Python Terminal or Web Dashboard.",
            color = TextSecondary,
            fontSize = 13.sp
        )

        Divider(color = BorderSubtle)

        // Backend URL Input
        OutlinedTextField(
            value = backendUrl,
            onValueChange = { backendUrl = it },
            label = { Text("Backend Server URL") },
            placeholder = { Text("http://10.0.2.2:8000 or http://192.168.1.50:8000") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AccentBlue,
                unfocusedBorderColor = BorderSubtle,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary
            )
        )

        // Device Label Input
        OutlinedTextField(
            value = deviceName,
            onValueChange = { deviceName = it },
            label = { Text("Device Label") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AccentBlue,
                unfocusedBorderColor = BorderSubtle,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary
            )
        )

        // PIN Input
        OutlinedTextField(
            value = pin,
            onValueChange = { if (it.length <= 6 && it.all { char -> char.isDigit() }) pin = it },
            label = { Text("6-Digit Pairing PIN") },
            placeholder = { Text("123456") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AccentBlue,
                unfocusedBorderColor = BorderSubtle,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary
            )
        )

        Spacer(modifier = Modifier.weight(1f))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(6.dp)
            ) {
                Text(text = "CANCEL", color = TextSecondary)
            }

            Button(
                onClick = {
                    if (pin.length == 6 && backendUrl.isNotBlank()) {
                        isSubmitting = true
                        onClaimPairing(pin, backendUrl.trim(), deviceName.trim())
                    }
                },
                enabled = pin.length == 6 && !isSubmitting,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                shape = RoundedCornerShape(6.dp)
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = DarkBackground)
                } else {
                    Text(text = "VERIFY & PAIR", color = DarkBackground, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
