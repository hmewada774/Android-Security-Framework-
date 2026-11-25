package com.asf.agent.security

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.util.UUID

class KeystoreHelper(context: Context) {

    private val prefs: SharedPreferences

    init {
        prefs = try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            EncryptedSharedPreferences.create(
                context,
                PREFS_FILENAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            Log.w(TAG, "Hardware Keystore encryption unavailable; falling back to private SharedPreferences", e)
            context.getSharedPreferences(PREFS_FILENAME + "_fallback", Context.MODE_PRIVATE)
        }
    }

    fun getDeviceId(): String {
        var id = prefs.getString(KEY_DEVICE_ID, null)
        if (id == null) {
            id = "asf_" + UUID.randomUUID().toString().replace("-", "").take(16)
            prefs.edit().putString(KEY_DEVICE_ID, id).apply()
        }
        return id
    }

    fun getDeviceModel(): String {
        return "${Build.MANUFACTURER} ${Build.MODEL}"
    }

    fun getOsVersion(): String {
        return "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})"
    }

    fun saveCredentials(deviceId: String, authToken: String, backendUrl: String) {
        prefs.edit()
            .putString(KEY_DEVICE_ID, deviceId)
            .putString(KEY_AUTH_TOKEN, authToken)
            .putString(KEY_BACKEND_URL, backendUrl)
            .putBoolean(KEY_IS_PAIRED, true)
            .apply()
    }

    fun getAuthToken(): String? = prefs.getString(KEY_AUTH_TOKEN, null)

    fun getBackendUrl(): String = prefs.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL) ?: DEFAULT_BACKEND_URL

    fun isPaired(): Boolean = prefs.getBoolean(KEY_IS_PAIRED, false) && !getAuthToken().isNullOrBlank()

    fun clearCredentials() {
        prefs.edit()
            .remove(KEY_AUTH_TOKEN)
            .putBoolean(KEY_IS_PAIRED, false)
            .apply()
    }

    companion object {
        private const val TAG = "ASF_Keystore"
        private const val PREFS_FILENAME = "asf_secure_credentials"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_IS_PAIRED = "is_paired"
        const val DEFAULT_BACKEND_URL = "http://10.0.2.2:8000" // Default for Android Emulator; physical devices use host IP or adb reverse
    }
}
