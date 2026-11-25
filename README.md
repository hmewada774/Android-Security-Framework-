# 🛡️ Android Security Framework (ASF)

**A Python-powered Android Security Monitoring and Device Diagnostics Framework with a Native Kotlin Agent, Real-Time Telemetry, Secure Wi-Fi Pairing, and a Live Web Dashboard.**

ASF is a security-focused Android monitoring framework designed for authorized testing and diagnostics on owner-controlled Android devices. It combines a native Android application with a Python-based backend to collect device telemetry, monitor connection events, analyze security activity, and provide consent-based remote screen sharing — all through a local network connection.

Built with **Kotlin, Jetpack Compose, Python, FastAPI, WebSockets, and SQLite**, ASF provides a lightweight, modular architecture without requiring complex frontend frameworks.

---

## 🚀 Key Features

- **📱 Native Android Agent:** Built with Kotlin and Jetpack Compose for Android device integration.
- **📡 Real-Time Device Telemetry:** Collect device diagnostics, including battery status, memory usage, charging state, and network information.
- **🔐 Secure Device Pairing:** Authenticate authorized devices using temporary pairing PINs and securely stored credentials.
- **🌐 Wi-Fi-Based Communication:** Connect Android devices to the local Python backend without requiring a persistent USB connection.
- **🖥️ Live Web Dashboard:** Monitor connected devices, telemetry, sessions, and security events through a browser-based interface.
- **📺 Consent-Based Screen Sharing:** Stream screen content using Android MediaProjection with explicit OS approval and a visible foreground notification.
- **⌨️ Sandboxed Typing Analytics:** Analyze typing speed, accuracy, and keystroke timing inside a dedicated in-app typing lab — without system-wide keylogging.
- **⚡ Asynchronous FastAPI Backend:** Handle REST APIs, authenticated WebSocket connections, and real-time event communication.
- **🗄️ SQLite Database:** Store device information, telemetry records, sessions, and security events using SQLite with WAL support.
- **🐍 Python CLI Controller:** Manage authorized devices, generate pairing codes, inspect system health, and monitor security events.
- **🔄 Modular Architecture:** Separate Android, backend, controller, dashboard, database, and testing components.

---

## 🏗️ Technology Stack

| Component | Technologies |
|---|---|
| Android Agent | Kotlin, Jetpack Compose |
| Android Security | Android Keystore, EncryptedSharedPreferences |
| Backend | Python, FastAPI |
| Communication | REST API, WebSockets |
| Dashboard | HTML5, CSS3, JavaScript |
| Database | SQLite, WAL |
| Screen Sharing | Android MediaProjection |
| Testing | Pytest |
| Development Environment | Kali Linux, Android SDK, Gradle |

---

## 📂 Project Architecture

```text
Android-Security-Framework/
│
├── controller/          # Python CLI controller
│
├── backend/             # FastAPI backend and APIs
│   ├── app/
│   ├── endpoints/
│   ├── schemas/
│   └── websocket/
│
├── dashboard/           # Web-based monitoring dashboard
│
├── android-agent/       # Native Kotlin Android application
│   └── app/
│
├── database/            # SQLite database and migrations
│
├── tests/               # Automated test suite
│
└── docs/                # Architecture and security documentation
```

---

## ⚙️ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Android-Security-Framework.git

cd Android-Security-Framework
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests

```bash
python3 -m pytest tests/
```

### 4. Start the Backend Server

For local-only dashboard access:

```bash
python3 -m uvicorn backend.app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

For trusted local Wi-Fi testing:

```bash
python3 -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Only use LAN binding on a trusted private network with appropriate firewall and authentication protections. Do not expose the development server directly to the public internet.

### 5. Open the Web Dashboard

```text
http://127.0.0.1:8000
```

### 6. Use the Python CLI Controller

Check backend health:

```bash
python3 controller/cli.py health
```

Generate a pairing code:

```bash
python3 controller/cli.py pair --name "Android Test Device"
```

List paired devices:

```bash
python3 controller/cli.py devices
```

---

## 📱 Android Application

The native Android agent is designed for Android 10 and later (API 29+).

Build the debug APK:

```bash
cd android-agent
./gradlew assembleDebug
```

APK output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

Install the APK on an authorized Android device and configure the backend address through the app's pairing interface.

---

## 🔒 Security and Privacy

ASF follows an authorization-first design:

- Device pairing requires a valid temporary pairing code.
- Authentication credentials are stored using Android secure storage.
- Screen sharing requires explicit Android OS MediaProjection approval.
- Screen capture operates through a visible foreground service.
- Typing analytics remain restricted to the dedicated in-app typing lab.
- No covert system-wide keylogging or password collection.
- No unauthorized permission bypasses or arbitrary remote shell execution.
- Device access and security events are tracked by the backend.

**Important:** Use ASF only on devices you own or have explicit authorization to test.

---

## 🎯 Project Goals

ASF aims to explore and demonstrate:

- Android application security and native development.
- Secure client-server communication.
- Real-time device monitoring using WebSockets.
- Python-based security automation.
- Android device telemetry and diagnostics.
- Consent-based remote screen streaming.
- Secure authentication and session management.
- Security event logging and monitoring dashboard design.

---

## 🛠️ Project Status

**Active Development**

The backend, dashboard, native Android agent scaffolding, and debug APK build have been completed. Wi-Fi pairing and initial agent connection have been demonstrated. Continuous telemetry delivery, connection stability, and broader device compatibility remain under testing.

---

## 👨‍💻 Author

**Hariom Mewada**

- GitHub: [@hariom774](https://github.com/hmewada774)
- LinkedIn: [Hariom Mewada](https://www.linkedin.com/in/hariom-mewada-cybersecurity/)

---

⭐ If you find this project interesting, consider giving it a star and following its development.
