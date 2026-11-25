package com.asf.agent.service

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.Looper
import android.util.Base64
import android.util.DisplayMetrics
import android.util.Log
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import com.asf.agent.MainActivity
import com.asf.agent.network.WebSocketManager
import com.asf.agent.security.KeystoreHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

/**
 * Foreground Service for authorized Android screen capture.
 *
 * Implements strict Android 10+ (API 29) to Android 15 (API 35) MediaProjection lifecycle:
 * - Requires explicit user consent via system prompt (MediaProjectionManager).
 * - Enforces mandatory MediaProjection.Callback registration BEFORE VirtualDisplay creation (API 34+ requirement).
 * - Manages idempotent teardown with non-recursive callbacks.
 * - Rejects duplicate capture start requests safely without overwriting active projections.
 * - Displays an ongoing non-dismissible notification with an explicit "Stop Monitoring" action.
 * - Downscales resolution to universal 720p at ~10 FPS for lightweight non-intrusive streaming.
 */
class ScreenCaptureService : Service() {

    private enum class CaptureState {
        IDLE,
        STARTING,
        CAPTURING,
        STOPPING
    }

    private val stateLock = Any()
    @Volatile
    private var captureState = CaptureState.IDLE

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var imageHandlerThread: HandlerThread? = null
    private var imageHandler: Handler? = null

    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private lateinit var webSocketManager: WebSocketManager
    private lateinit var keystoreHelper: KeystoreHelper

    private var lastFrameTime = 0L
    private val frameIntervalMs = 100L // Cap at ~10 FPS for lightweight streaming

    /**
     * Android MediaProjection callback.
     * Android 14+ requires this callback to be registered before createVirtualDisplay().
     * Invoked when the projection session stops (user revokes consent in system UI or OS terminates session).
     */
    private val projectionCallback = object : MediaProjection.Callback() {
        override fun onStop() {
            Log.i(TAG, "MediaProjection.Callback.onStop() received: session ended by OS or user")
            stopCapture()
            stopSelf()
        }
    }

    override fun onCreate() {
        super.onCreate()
        keystoreHelper = KeystoreHelper(this)
        webSocketManager = WebSocketManager(keystoreHelper)
        webSocketManager.connect()
        webSocketManager.onStopStreamRequested = {
            Log.i(TAG, "Operator remote STOP_STREAM requested via WebSocket")
            stopCapture()
            stopSelf()
        }
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) return START_NOT_STICKY

        val action = intent.action
        if (action == ACTION_STOP) {
            Log.i(TAG, "ACTION_STOP command received")
            stopCapture()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_REMOVE)
            } else {
                @Suppress("DEPRECATION")
                stopForeground(true)
            }
            stopSelf()
            return START_NOT_STICKY
        }

        if (action == ACTION_START) {
            synchronized(stateLock) {
                if (captureState != CaptureState.IDLE) {
                    Log.w(TAG, "ACTION_START rejected: capture session already active/starting (state=$captureState)")
                    return START_NOT_STICKY
                }
                captureState = CaptureState.STARTING
            }

            val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
            val resultData = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(EXTRA_RESULT_DATA)
            }

            if (resultCode != Activity.RESULT_OK || resultData == null) {
                Log.e(TAG, "Invalid consent result: code=$resultCode, data=$resultData")
                synchronized(stateLock) { captureState = CaptureState.IDLE }
                stopSelf()
                return START_NOT_STICKY
            }

            startForegroundNotification()
            startProjection(resultCode, resultData)

            return START_STICKY
        }

        return START_NOT_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "ASF Security Monitoring",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Active screen capture indicator for authorized testing"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun startForegroundNotification() {
        val stopIntent = Intent(this, ScreenCaptureService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this,
            1,
            stopIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val openAppIntent = Intent(this, MainActivity::class.java)
        val openAppPendingIntent = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("ASF Monitoring Active")
            .setContentText("Screen sharing is active with user authorization.")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(openAppPendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop Monitoring", stopPendingIntent)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun startProjection(resultCode: Int, resultData: Intent) {
        try {
            val mpManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val mp = mpManager.getMediaProjection(resultCode, resultData)

            if (mp == null) {
                Log.e(TAG, "Failed to obtain MediaProjection token from MediaProjectionManager")
                synchronized(stateLock) { captureState = CaptureState.IDLE }
                stopSelf()
                return
            }
            mediaProjection = mp

            // Dedicated HandlerThread to process incoming image frames off the main thread
            val thread = HandlerThread("ASF_ImageReaderThread").apply { start() }
            imageHandlerThread = thread
            val handler = Handler(thread.looper)
            imageHandler = handler

            // MANDATORY ON ANDROID 14+ (API 34+):
            // Register callback BEFORE calling createVirtualDisplay()
            mp.registerCallback(projectionCallback, handler)

            val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val metrics = DisplayMetrics()
            @Suppress("DEPRECATION")
            windowManager.defaultDisplay.getRealMetrics(metrics)

            // Scale resolution to 720p equivalent for lightweight universal streaming
            val targetWidth = 720
            val targetHeight = (720 * (metrics.heightPixels.toDouble() / metrics.widthPixels)).toInt()
            val density = metrics.densityDpi

            val reader = ImageReader.newInstance(targetWidth, targetHeight, PixelFormat.RGBA_8888, 2)
            imageReader = reader

            val vd = mp.createVirtualDisplay(
                "ASF_VirtualDisplay",
                targetWidth,
                targetHeight,
                density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                reader.surface,
                null,
                null
            )
            virtualDisplay = vd

            synchronized(stateLock) {
                captureState = CaptureState.CAPTURING
                isServiceCapturing = true
            }

            webSocketManager.sendSessionState("active", "screen_share")

            reader.setOnImageAvailableListener({ r ->
                val now = System.currentTimeMillis()
                if (now - lastFrameTime < frameIntervalMs) {
                    // Drop frame to cap frame rate and maintain low CPU usage
                    val dropped = r.acquireLatestImage()
                    dropped?.close()
                    return@setOnImageAvailableListener
                }
                lastFrameTime = now

                val image = r.acquireLatestImage() ?: return@setOnImageAvailableListener
                serviceScope.launch {
                    processAndSendFrame(image, targetWidth, targetHeight)
                }
            }, handler)

        } catch (e: Exception) {
            Log.e(TAG, "Initialization failed in startProjection: ${e.message}", e)
            stopCapture()
            stopSelf()
        }
    }

    private fun processAndSendFrame(image: Image, width: Int, height: Int) {
        try {
            val planes = image.planes
            val buffer = planes[0].buffer
            val pixelStride = planes[0].pixelStride
            val rowStride = planes[0].rowStride
            val rowPadding = rowStride - pixelStride * width

            val bitmap = Bitmap.createBitmap(
                width + rowPadding / pixelStride,
                height,
                Bitmap.Config.ARGB_8888
            )
            bitmap.copyPixelsFromBuffer(buffer)
            image.close()

            // Crop to actual width if padded
            val finalBitmap = if (rowPadding != 0) {
                Bitmap.createBitmap(bitmap, 0, 0, width, height)
            } else {
                bitmap
            }

            // Compress to JPEG with 50% quality for network efficiency
            val outputStream = ByteArrayOutputStream()
            finalBitmap.compress(Bitmap.CompressFormat.JPEG, 50, outputStream)
            val jpegBytes = outputStream.toByteArray()
            val base64Frame = Base64.encodeToString(jpegBytes, Base64.NO_WRAP)

            webSocketManager.sendFrame(base64Frame)
            if (finalBitmap != bitmap) {
                bitmap.recycle()
            }
            finalBitmap.recycle()
        } catch (e: Exception) {
            Log.e(TAG, "Frame processing error: ${e.message}")
            try { image.close() } catch (_: Exception) {}
        }
    }

    /**
     * Idempotent teardown sequence:
     * - Protected by stateLock and CaptureState to prevent recursive or duplicate invocation.
     * - Detaches listeners, releases VirtualDisplay, closes ImageReader, terminates HandlerThread.
     * - Safely stops and unregisters MediaProjection.
     */
    private fun stopCapture() {
        synchronized(stateLock) {
            if (captureState == CaptureState.IDLE || captureState == CaptureState.STOPPING) {
                return
            }
            captureState = CaptureState.STOPPING
        }

        try {
            // 1. Detach image listener to prevent processing queued frames during teardown
            imageReader?.setOnImageAvailableListener(null, null)

            // 2. Release virtual display
            virtualDisplay?.release()
            virtualDisplay = null

            // 3. Close image reader
            imageReader?.close()
            imageReader = null

            // 4. Safely stop HandlerThread
            imageHandlerThread?.quitSafely()
            imageHandlerThread = null
            imageHandler = null

            // 5. Unregister callback and stop MediaProjection safely
            mediaProjection?.let { mp ->
                try {
                    mp.unregisterCallback(projectionCallback)
                } catch (e: Exception) {
                    Log.w(TAG, "Warning unregistering projectionCallback: ${e.message}")
                }
                try {
                    mp.stop()
                } catch (e: Exception) {
                    Log.w(TAG, "Warning stopping MediaProjection: ${e.message}")
                }
            }
            mediaProjection = null

            // 6. Notify operator via WebSocket that stream has stopped
            webSocketManager.sendSessionState("stopped", "screen_share")
        } catch (e: Exception) {
            Log.e(TAG, "Teardown error in stopCapture: ${e.message}", e)
        } finally {
            synchronized(stateLock) {
                captureState = CaptureState.IDLE
                isServiceCapturing = false
            }
        }
    }

    override fun onDestroy() {
        stopCapture()
        webSocketManager.disconnect()
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "ASF_CaptureService"
        const val CHANNEL_ID = "asf_monitoring_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START = "com.asf.agent.START_CAPTURE"
        const val ACTION_STOP = "com.asf.agent.STOP_CAPTURE"
        const val EXTRA_RESULT_CODE = "extra_result_code"
        const val EXTRA_RESULT_DATA = "extra_result_data"

        @Volatile
        var isServiceCapturing: Boolean = false
            private set
    }
}
