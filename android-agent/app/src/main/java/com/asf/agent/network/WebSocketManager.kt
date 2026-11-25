package com.asf.agent.network

import android.util.Log
import com.asf.agent.security.KeystoreHelper
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.*
import java.util.concurrent.TimeUnit

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    REVOKED,
    ERROR
}

class WebSocketManager(private val keystoreHelper: KeystoreHelper) {

    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // Indefinite read for WebSockets
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _connectionStatus = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus.asStateFlow()

    var onStopStreamRequested: (() -> Unit)? = null
    var onStartStreamRequested: ((sessionId: String) -> Unit)? = null

    fun connect() {
        val token = keystoreHelper.getAuthToken()
        if (token.isNullOrBlank()) {
            _connectionStatus.value = ConnectionStatus.DISCONNECTED
            return
        }

        if (_connectionStatus.value == ConnectionStatus.CONNECTED || _connectionStatus.value == ConnectionStatus.CONNECTING) {
            return
        }

        _connectionStatus.value = ConnectionStatus.CONNECTING
        val rawBackendUrl = keystoreHelper.getBackendUrl().trim().trimEnd('/')
        val backendUrl = if (!rawBackendUrl.startsWith("http://", ignoreCase = true) &&
            !rawBackendUrl.startsWith("https://", ignoreCase = true)
        ) {
            "http://$rawBackendUrl"
        } else {
            rawBackendUrl
        }
        val wsUrl = backendUrl.replaceFirst("http://", "ws://", ignoreCase = true)
            .replaceFirst("https://", "wss://", ignoreCase = true) +
                "/ws/agent?token=" + token

        val request = Request.Builder().url(wsUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Agent WebSocket connection established")
                _connectionStatus.value = ConnectionStatus.CONNECTED
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleInboundMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.w(TAG, "Agent WebSocket closing: $code / $reason")
                if (code == 1008) {
                    _connectionStatus.value = ConnectionStatus.REVOKED
                } else {
                    _connectionStatus.value = ConnectionStatus.DISCONNECTED
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (code == 1008) {
                    _connectionStatus.value = ConnectionStatus.REVOKED
                    keystoreHelper.clearCredentials()
                } else {
                    _connectionStatus.value = ConnectionStatus.DISCONNECTED
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "Agent WebSocket failure: ${t.message}")
                _connectionStatus.value = ConnectionStatus.ERROR
                scheduleReconnect()
            }
        })
    }

    private fun handleInboundMessage(rawText: String) {
        try {
            val json = gson.fromJson(rawText, JsonObject::class.java)
            val command = json.get("command")?.asString
            when (command) {
                "STOP_STREAM" -> {
                    Log.i(TAG, "Remote STOP_STREAM command received from operator")
                    onStopStreamRequested?.invoke()
                }
                "START_STREAM" -> {
                    val sessionId = json.get("session_id")?.asString ?: "active_session"
                    Log.i(TAG, "Remote START_STREAM command received: $sessionId")
                    onStartStreamRequested?.invoke(sessionId)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing server message: $rawText", e)
        }
    }

    fun sendFrame(base64Jpeg: String) {
        if (_connectionStatus.value != ConnectionStatus.CONNECTED) return
        val payload = JsonObject().apply {
            addProperty("type", "screen_frame")
            addProperty("frame", base64Jpeg)
        }
        webSocket?.send(payload.toString())
    }

    fun sendSessionState(state: String, sessionType: String = "screen_share", sessionId: String? = null) {
        if (_connectionStatus.value != ConnectionStatus.CONNECTED) return
        val payload = JsonObject().apply {
            addProperty("type", "session_state")
            addProperty("state", state)
            addProperty("session_type", sessionType)
            sessionId?.let { addProperty("session_id", it) }
        }
        webSocket?.send(payload.toString())
    }

    fun sendHeartbeat() {
        if (_connectionStatus.value != ConnectionStatus.CONNECTED) return
        val payload = JsonObject().apply {
            addProperty("type", "heartbeat")
        }
        webSocket?.send(payload.toString())
    }

    fun disconnect() {
        webSocket?.close(1000, "App closed")
        webSocket = null
        _connectionStatus.value = ConnectionStatus.DISCONNECTED
    }

    private fun scheduleReconnect() {
        scope.launch {
            delay(5000)
            if (_connectionStatus.value != ConnectionStatus.CONNECTED && _connectionStatus.value != ConnectionStatus.REVOKED) {
                connect()
            }
        }
    }

    companion object {
        private const val TAG = "ASF_WebSocket"
    }
}
