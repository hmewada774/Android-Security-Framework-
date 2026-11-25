# Android Agent Initialization & Gradle Guide

## Overview
The `android-agent` module is designed as a native Android application using Kotlin and Jetpack Compose.

## Prerequisites for Android Build
1. **JDK:** OpenJDK 17 or OpenJDK 21 LTS.
2. **Android SDK:**
   - Platform: `android-34` (Android 14) or `android-35` (Android 15)
   - Build Tools: `34.0.0`
   - Platform Tools (`adb`)
3. **Gradle:** 8.4+ with Android Gradle Plugin (AGP) 8.3+.

## Required Android Permissions (in `AndroidManifest.xml`)
```xml
<!-- Internet and Network Monitoring -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<!-- Foreground Service for Persistent Session Indicator -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

## Running against Local Host & LAN Development

### Option A: ADB Reverse (Recommended for USB Debugging)
When testing on a physical device over USB or Android Emulator:
```bash
# Forward local backend port 8000 to the connected Android device
adb reverse tcp:8000 tcp:8000
```
In the Android app pairing screen, set Backend URL to:
`http://127.0.0.1:8000` (or `http://localhost:8000`)

### Option B: Local Wi-Fi / LAN
Ensure the Android test device and development workstation are connected to the same Wi-Fi subnet. In the Android app pairing screen, enter:
`http://<WORKSTATION_LAN_IP>:8000` (e.g., `http://192.168.1.50:8000`)

## Network Security Configuration Architecture
- **Debug Builds (`assembleDebug`):**
  Uses `app/src/debug/res/xml/network_security_config.xml` and `app/src/debug/AndroidManifest.xml` (`android:usesCleartextTraffic="true"`). Cleartext traffic (`http://` and `ws://`) is permitted strictly for local development and authorized testing against local hosts.
- **Release Builds (`assembleRelease`):**
  Uses `app/src/main/res/xml/network_security_config.xml` (`<base-config cleartextTrafficPermitted="false">`). Cleartext traffic is strictly blocked; only HTTPS and WSS connections are permitted.

## MediaProjection Security & Lifecycle
- **Android 14+ (API 34+) Compliance:**
  `MediaProjection.registerCallback()` is registered prior to `createVirtualDisplay()`. Failure to register this callback causes an immediate unhandled `IllegalStateException` on Android 14+.
- **Idempotent Teardown:**
  `ScreenCaptureService` manages an atomic `CaptureState` machine (`IDLE`, `STARTING`, `CAPTURING`, `STOPPING`) to prevent recursive calls during system-initiated stops and safely clean up the `VirtualDisplay`, `ImageReader`, and background handler thread. Duplicate start requests are rejected safely.

