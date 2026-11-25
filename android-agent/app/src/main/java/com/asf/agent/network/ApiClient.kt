package com.asf.agent.network

import com.asf.agent.security.KeystoreHelper
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.net.URI
import java.util.concurrent.TimeUnit

data class PairingClaimResult(
    val success: Boolean,
    val authToken: String? = null,
    val message: String
)

data class TelemetryData(
    val deviceId: String,
    val batteryLevel: Int?,
    val isCharging: Boolean?,
    val networkType: String?,
    val cpuUsage: Double? = null,
    val ramUsageMb: Double? = null,
    val sessionId: String? = null
)

data class TypingSessionData(
    val deviceId: String,
    val testPromptId: String,
    val wpm: Double,
    val accuracyPercent: Double,
    val avgFlightTimeMs: Double,
    val avgHoldTimeMs: Double,
    val totalKeystrokes: Int,
    val errorCount: Int,
    val sessionId: String? = null
)

class ApiClient(private val keystoreHelper: KeystoreHelper) {

    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    suspend fun claimPairing(
        pin: String,
        backendUrl: String,
        deviceName: String
    ): Result<PairingClaimResult> = withContext(Dispatchers.IO) {
        try {
            val deviceId = keystoreHelper.getDeviceId()
            val model = keystoreHelper.getDeviceModel()
            val osVersion = keystoreHelper.getOsVersion()

            val payload = JsonObject().apply {
                addProperty("pairing_pin", pin)
                addProperty("device_id", deviceId)
                addProperty("device_name", deviceName)
                addProperty("model", model)
                addProperty("os_version", osVersion)
            }

            val cleanUrl = validateBackendUrl(backendUrl)
            val request = Request.Builder()
                .url("$cleanUrl/api/v1/pairing/claim")
                .post(payload.toString().toRequestBody(jsonMediaType))
                .build()

            httpClient.newCall(request).execute().use { response ->
                val body = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    val json = gson.fromJson(body, JsonObject::class.java)
                    val token = json.get("auth_token")?.asString
                    if (!token.isNullOrBlank()) {
                        keystoreHelper.saveCredentials(deviceId, token, cleanUrl)
                        Result.success(PairingClaimResult(true, token, "Device paired successfully."))
                    } else {
                        Result.failure(Exception("Auth token missing from server response."))
                    }
                } else {
                    Result.failure(Exception("Pairing failed (HTTP ${response.code}): $body"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun sendTelemetry(data: TelemetryData): Result<Boolean> = withContext(Dispatchers.IO) {
        val token = keystoreHelper.getAuthToken()
            ?: return@withContext Result.failure(Exception("Device not paired: missing auth token"))
        val backendUrl = validateBackendUrl(keystoreHelper.getBackendUrl())

        try {
            val payload = JsonObject().apply {
                addProperty("device_id", data.deviceId)
                data.batteryLevel?.let { addProperty("battery_level", it) }
                data.isCharging?.let { addProperty("is_charging", it) }
                data.networkType?.let { addProperty("network_type", it) }
                data.cpuUsage?.let { addProperty("cpu_usage", it) }
                data.ramUsageMb?.let { addProperty("ram_usage_mb", it) }
                data.sessionId?.let { addProperty("session_id", it) }
            }

            val request = Request.Builder()
                .url("$backendUrl/api/v1/telemetry/report")
                .addHeader("Authorization", "Bearer $token")
                .post(payload.toString().toRequestBody(jsonMediaType))
                .build()

            httpClient.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    Result.success(true)
                } else {
                    Result.failure(Exception("Telemetry failed: HTTP ${response.code}"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitTypingBenchmark(data: TypingSessionData): Result<Boolean> = withContext(Dispatchers.IO) {
        val token = keystoreHelper.getAuthToken()
            ?: return@withContext Result.failure(Exception("Device not paired: missing auth token"))
        val backendUrl = validateBackendUrl(keystoreHelper.getBackendUrl())

        try {
            val payload = JsonObject().apply {
                addProperty("device_id", data.deviceId)
                addProperty("test_prompt_id", data.testPromptId)
                addProperty("wpm", data.wpm)
                addProperty("accuracy_percent", data.accuracyPercent)
                addProperty("avg_flight_time_ms", data.avgFlightTimeMs)
                addProperty("avg_hold_time_ms", data.avgHoldTimeMs)
                addProperty("total_keystrokes", data.totalKeystrokes)
                addProperty("error_count", data.errorCount)
                data.sessionId?.let { addProperty("session_id", it) }
            }

            val request = Request.Builder()
                .url("$backendUrl/api/v1/typing/session")
                .addHeader("Authorization", "Bearer $token")
                .post(payload.toString().toRequestBody(jsonMediaType))
                .build()

            httpClient.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    Result.success(true)
                } else {
                    Result.failure(Exception("Typing benchmark rejected: HTTP ${response.code}"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    companion object {
        fun validateBackendUrl(rawUrl: String): String {
            val trimmed = rawUrl.trim().trimEnd('/')
            require(trimmed.isNotBlank()) { "Backend URL cannot be blank." }

            val urlWithScheme = if (!trimmed.startsWith("http://", ignoreCase = true) &&
                !trimmed.startsWith("https://", ignoreCase = true)
            ) {
                "http://$trimmed"
            } else {
                trimmed
            }

            val uri = URI(urlWithScheme)
            val scheme = uri.scheme?.lowercase()
            require(scheme == "http" || scheme == "https") {
                "Invalid protocol '${uri.scheme}'. Only http:// and https:// are supported."
            }
            require(!uri.host.isNullOrBlank()) {
                "Invalid backend URL: hostname or IP address is required."
            }
            return urlWithScheme
        }
    }
}
