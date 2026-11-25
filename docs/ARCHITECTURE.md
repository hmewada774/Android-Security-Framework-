# Android Security Framework (ASF) — Architecture & Security Model

## 1. Executive Summary
The Android Security Framework (ASF) is a non-covert, authorized mobile security testing application. It couples a native Kotlin/Jetpack Compose Android client with a Python terminal controller, FastAPI backend, and local web dashboard.

---

## 2. Core Security Guarantees & Constraints
- **Explicit Consent for Screen Sharing:** Screen capture strictly utilizes Android's official `MediaProjectionManager`. The Android operating system enforces an un-bypassable confirmation dialog with the user before any projection token is granted.
- **Unambiguous Session Notification:** While screen sharing or telemetry collection is active, Android requires a persistent Foreground Service with an ongoing notification. The user retains continuous visibility and can terminate the session at any moment directly from the notification tray.
- **Dedicated Typing Lab Isolation:** Keystroke analytics (flight time, hold time, WPM, and error rate) are measured **solely** inside a dedicated, sandboxed test screen in the app. ASF does **not** register an `AccessibilityService` or attempt system-wide keylogging. It captures zero user passwords or private messages.
- **Mutual Device Pairing:** Devices authenticate via time-limited 6-digit numeric PINs exchanged out-of-band and verified against a local SQLite database. Paired sessions receive unique 256-bit cryptographic tokens stored in Android's secure `EncryptedSharedPreferences` backed by the Android Keystore.

---

## 3. Communication & Protocol Specs
- **REST Endpoints (`/api/v1`):** Used for out-of-band device pairing, telemetry heartbeat delivery, typing benchmark persistence, and device revocation.
- **WebSocket Protocol (`/ws`):**
  - `/ws/agent?token=<auth_token>`: High-frequency frame streaming and real-time state notification from the Android agent.
  - `/ws/dashboard`: Fan-out stream to local web browsers and terminal CLI observers.
