package com.asf.agent

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.asf.agent.network.*
import com.asf.agent.security.KeystoreHelper
import com.asf.agent.service.ScreenCaptureService
import com.asf.agent.ui.screens.*
import com.asf.agent.ui.theme.ASFAgentTheme
import kotlinx.coroutines.launch

enum class ScreenState {
    HOME,
    PAIRING,
    SCREEN_SHARE,
    TYPING_LAB
}

class MainActivity : ComponentActivity() {

    private lateinit var keystoreHelper: KeystoreHelper
    private lateinit var apiClient: ApiClient
    private lateinit var webSocketManager: WebSocketManager

    private var isStreamingActive by mutableStateOf(false)

    // MediaProjection Activity Result Launcher
    private val projectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val serviceIntent = Intent(this, ScreenCaptureService::class.java).apply {
                action = ScreenCaptureService.ACTION_START
                putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(ScreenCaptureService.EXTRA_RESULT_DATA, result.data)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
            isStreamingActive = true
            Toast.makeText(this, "Screen capture service started", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Screen capture consent denied by user", Toast.LENGTH_SHORT).show()
        }
    }

    // Android 13+ Notification Permission Launcher
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (!isGranted) {
            Toast.makeText(this, "Notification permission required for active session indicator", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        keystoreHelper = KeystoreHelper(this)
        apiClient = ApiClient(keystoreHelper)
        webSocketManager = WebSocketManager(keystoreHelper)

        if (keystoreHelper.isPaired()) {
            webSocketManager.connect()
        }

        checkNotificationPermission()

        setContent {
            ASFAgentTheme {
                val connectionStatus by webSocketManager.connectionStatus.collectAsState()
                var currentScreen by remember { mutableStateOf(ScreenState.HOME) }

                when (currentScreen) {
                    ScreenState.HOME -> {
                        HomeScreen(
                            isPaired = keystoreHelper.isPaired(),
                            deviceId = keystoreHelper.getDeviceId(),
                            deviceModel = keystoreHelper.getDeviceModel(),
                            osVersion = keystoreHelper.getOsVersion(),
                            backendUrl = keystoreHelper.getBackendUrl(),
                            connectionStatus = connectionStatus,
                            onNavigateToPairing = { currentScreen = ScreenState.PAIRING },
                            onNavigateToScreenShare = { currentScreen = ScreenState.SCREEN_SHARE },
                            onNavigateToTypingLab = { currentScreen = ScreenState.TYPING_LAB },
                            onSendTelemetry = { postLiveTelemetry() }
                        )
                    }
                    ScreenState.PAIRING -> {
                        PairingScreen(
                            currentBackendUrl = keystoreHelper.getBackendUrl(),
                            onClaimPairing = { pin, url, name ->
                                handleClaimPairing(pin, url, name) {
                                    currentScreen = ScreenState.HOME
                                }
                            },
                            onCancel = { currentScreen = ScreenState.HOME }
                        )
                    }
                    ScreenState.SCREEN_SHARE -> {
                        ScreenShareScreen(
                            isStreaming = isStreamingActive,
                            onStartRequested = { requestScreenCaptureConsent() },
                            onStopRequested = { stopScreenCapture() },
                            onBack = { currentScreen = ScreenState.HOME }
                        )
                    }
                    ScreenState.TYPING_LAB -> {
                        TypingLabScreen(
                            deviceId = keystoreHelper.getDeviceId(),
                            onSubmitBenchmark = { data ->
                                lifecycleScope.launch {
                                    val res = apiClient.submitTypingBenchmark(data)
                                    if (res.isSuccess) {
                                        Toast.makeText(this@MainActivity, "Typing benchmark saved to audit log", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Toast.makeText(this@MainActivity, "Submission failed: ${res.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
                                    }
                                }
                            },
                            onBack = { currentScreen = ScreenState.HOME }
                        )
                    }
                }
            }
        }
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun requestScreenCaptureConsent() {
        val mpManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val intent = mpManager.createScreenCaptureIntent()
        projectionLauncher.launch(intent)
    }

    private fun stopScreenCapture() {
        val stopIntent = Intent(this, ScreenCaptureService::class.java).apply {
            action = ScreenCaptureService.ACTION_STOP
        }
        startService(stopIntent)
        isStreamingActive = false
        Toast.makeText(this, "Screen capture stopped", Toast.LENGTH_SHORT).show()
    }

    private fun handleClaimPairing(pin: String, url: String, name: String, onSuccess: () -> Unit) {
        lifecycleScope.launch {
            val result = apiClient.claimPairing(pin, url, name)
            if (result.isSuccess) {
                Toast.makeText(this@MainActivity, "Device paired successfully!", Toast.LENGTH_SHORT).show()
                webSocketManager.connect()
                onSuccess()
            } else {
                Toast.makeText(this@MainActivity, "Pairing error: ${result.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun postLiveTelemetry() {
        lifecycleScope.launch {
            val batteryManager = getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
            val batteryLevel = batteryManager?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: 80

            val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            val activeNetwork = connectivityManager?.activeNetwork
            val capabilities = connectivityManager?.getNetworkCapabilities(activeNetwork)
            val networkType = when {
                capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true -> "Wi-Fi"
                capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true -> "Cellular (Mobile)"
                capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) == true -> "Ethernet"
                else -> "Active Network"
            }

            val telemetry = TelemetryData(
                deviceId = keystoreHelper.getDeviceId(),
                batteryLevel = batteryLevel,
                isCharging = false,
                networkType = networkType
            )

            val res = apiClient.sendTelemetry(telemetry)
            if (res.isSuccess) {
                Toast.makeText(this@MainActivity, "Telemetry posted to dashboard", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this@MainActivity, "Telemetry error: ${res.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        isStreamingActive = ScreenCaptureService.isServiceCapturing
    }

    override fun onDestroy() {
        webSocketManager.disconnect()
        super.onDestroy()
    }
}
