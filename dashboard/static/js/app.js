// Android Security Framework (ASF) — Local Control Dashboard
(function () {
    const API_BASE = "/api/v1";
    let dashToken = "";
    let ws = null;
    let pinInterval = null;

    // State cache
    let cachedDevices = [];
    let connectedDeviceIds = new Set();
    let selectedTelemetryDevice = "";
    let selectedMonitoringDevice = "";

    // DOM Elements
    const dot = document.getElementById("connectionDot");
    const statusText = document.getElementById("connectionStatusText");
    const activeBanner = document.getElementById("activeSessionBanner");
    const btnBannerEmergencyStop = document.getElementById("btnBannerEmergencyStop");

    // Screen Viewport Elements
    const screenCanvas = document.getElementById("screenCanvas");
    const canvasCtx = screenCanvas ? screenCanvas.getContext("2d") : null;
    const viewportPlaceholder = document.getElementById("viewportPlaceholder");
    const viewportStatusText = document.getElementById("viewportStatusText");
    const viewportResolutionBadge = document.getElementById("viewportResolutionBadge");

    // Modals
    const pairModal = document.getElementById("pairModal");
    const deviceDetailsModal = document.getElementById("deviceDetailsModal");
    const deviceDetailsContent = document.getElementById("deviceDetailsContent");

    // Initialize Dashboard
    async function init() {
        setupNavigation();
        setupModals();
        setupTypingLab();
        setupMonitoringControls();
        setupExportControls();

        await fetchDashboardToken();
        connectWebSocket();
        await refreshAllData();
    }

    // Tab Navigation
    function setupNavigation() {
        const navItems = document.querySelectorAll(".nav-item");
        navItems.forEach(item => {
            item.addEventListener("click", () => {
                const targetTab = item.getAttribute("data-tab");
                switchTab(targetTab);
            });
        });
    }

    window.switchTab = function (tabId) {
        document.querySelectorAll(".nav-item").forEach(el => {
            if (el.getAttribute("data-tab") === tabId) {
                el.classList.add("active");
            } else {
                el.classList.remove("active");
            }
        });

        document.querySelectorAll(".tab-pane").forEach(pane => {
            if (pane.id === tabId) {
                pane.classList.add("active");
            } else {
                pane.classList.remove("active");
            }
        });

        if (tabId === "tab-overview") loadOverview();
        if (tabId === "tab-devices") loadDevices();
        if (tabId === "tab-monitoring") loadMonitoring();
        if (tabId === "tab-telemetry") loadTelemetryForSelected();
        if (tabId === "tab-events") loadSecurityEvents();
    };

    // Modal helpers
    function setupModals() {
        document.getElementById("btnOpenPairModal").addEventListener("click", () => {
            document.getElementById("pairModal").classList.add("active");
        });

        document.getElementById("btnGeneratePin").addEventListener("click", generatePairingPin);
    }

    window.closeModal = function (modalId) {
        const m = document.getElementById(modalId);
        if (m) m.classList.remove("active");
    };

    // Authenticate & Connect WebSocket
    async function fetchDashboardToken() {
        try {
            const res = await fetch(`${API_BASE}/auth/dashboard-token`);
            if (res.ok) {
                const data = await res.json();
                dashToken = data.token;
            }
        } catch (err) {
            console.error("Could not fetch dashboard session token", err);
        }
    }

    function connectWebSocket() {
        if (!dashToken) return;
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard?token=${encodeURIComponent(dashToken)}`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            dot.classList.add("online");
            statusText.textContent = "Backend Online (Connected)";
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWsEvent(msg);
            } catch (err) {
                console.error("Malformed WebSocket message", err);
            }
        };

        ws.onclose = () => {
            dot.classList.remove("online");
            statusText.textContent = "Backend Offline (Reconnecting...)";
            setTimeout(connectWebSocket, 3000);
        };
    }

    function handleWsEvent(msg) {
        switch (msg.event) {
            case "AGENT_CONNECTED":
                connectedDeviceIds.add(msg.device_id);
                refreshOverviewCounters();
                loadDevices();
                break;
            case "AGENT_DISCONNECTED":
                connectedDeviceIds.delete(msg.device_id);
                refreshOverviewCounters();
                loadDevices();
                if (selectedMonitoringDevice === msg.device_id) {
                    resetScreenStreamView("Agent Disconnected");
                }
                break;
            case "SESSION_STATE":
                updateSessionStateUI(msg.state, msg.device_id);
                break;
            case "SCREEN_FRAME":
                renderScreenFrame(msg.data, msg.device_id);
                break;
            case "TELEMETRY_UPDATE":
                handleLiveTelemetry(msg.data);
                break;
            case "TYPING_BENCHMARK_RECORDED":
                loadTypingAuditLog();
                break;
        }
    }

    // Refresh all data
    async function refreshAllData() {
        await loadOverview();
        await loadDevices();
        await loadMonitoring();
        await loadSecurityEvents();
    }

    // MODULE 1: Overview
    async function loadOverview() {
        try {
            const res = await fetch(`${API_BASE}/overview`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById("overviewBackendStatus").textContent = data.status.toUpperCase();
                document.getElementById("overviewVersion").textContent = `FastAPI Framework v${data.version}`;
                document.getElementById("overviewTotalDevices").textContent = data.total_paired_devices;
                document.getElementById("overviewConnectedAgents").textContent = data.connected_devices;
                document.getElementById("overviewActiveSessions").textContent = data.active_monitoring_sessions;

                connectedDeviceIds = new Set(data.connected_device_ids || []);
                renderOverviewEvents(data.recent_events || []);
            }
        } catch (err) {
            console.error("Failed to fetch overview metrics", err);
        }
    }

    function refreshOverviewCounters() {
        document.getElementById("overviewConnectedAgents").textContent = connectedDeviceIds.size;
    }

    function renderOverviewEvents(events) {
        const tbody = document.getElementById("overviewEventsBody");
        if (!events || events.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No security events recorded yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = events.map(e => `
            <tr>
                <td>${formatTimestamp(e.event_timestamp)}</td>
                <td><code>${escapeHtml(e.device_id || "System")}</code></td>
                <td><span class="badge badge-pending">${escapeHtml(e.event_type)}</span></td>
                <td><span class="badge ${getStatusBadgeClass(e.event_status)}">${escapeHtml(e.event_status)}</span></td>
                <td>${escapeHtml(e.details || "—")}</td>
            </tr>
        `).join("");
    }

    // MODULE 2: Device Management
    async function loadDevices() {
        try {
            const res = await fetch(`${API_BASE}/pairing/devices`);
            if (res.ok) {
                cachedDevices = await res.json();
                renderDevicesTable(cachedDevices);
                updateDeviceDropdowns(cachedDevices);
            }
        } catch (err) {
            console.error("Failed to load devices", err);
        }
    }

    function renderDevicesTable(devices) {
        const tbody = document.getElementById("devicesTableBody");
        document.getElementById("deviceListCounter").textContent = `${devices.length} device${devices.length === 1 ? '' : 's'}`;

        if (!devices || devices.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No devices registered. Click "Pair New Device" to initiate.</td></tr>`;
            return;
        }

        tbody.innerHTML = devices.map(d => {
            const isConnected = connectedDeviceIds.has(d.device_id);
            const statusBadge = d.status === 'paired' 
                ? `<span class="badge badge-paired">PAIRED</span>` 
                : `<span class="badge badge-revoked">REVOKED</span>`;
            
            const liveBadge = isConnected
                ? `<span class="badge badge-paired">ONLINE</span>`
                : `<span class="badge badge-stopped">OFFLINE</span>`;

            return `
                <tr>
                    <td><strong>${escapeHtml(d.device_name || "Unknown")}</strong></td>
                    <td><code>${escapeHtml(d.device_id)}</code></td>
                    <td>${escapeHtml(d.model || "Unknown")} &bull; ${escapeHtml(d.os_version || "Android")}</td>
                    <td>${statusBadge}</td>
                    <td>${liveBadge}</td>
                    <td>${formatTimestamp(d.last_seen_at)}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm" onclick="viewDeviceDetails('${escapeHtml(d.device_id)}')">Details</button>
                        ${d.status === 'paired' ? `<button class="btn btn-danger btn-sm" onclick="revokeDeviceAccess('${escapeHtml(d.device_id)}')">Revoke</button>` : ''}
                        <button class="btn btn-secondary btn-sm" onclick="filterEventsForDevice('${escapeHtml(d.device_id)}')">History</button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    function updateDeviceDropdowns(devices) {
        const pairedDevices = devices.filter(d => d.status === 'paired');
        
        // Monitoring select
        const monSelect = document.getElementById("monitoringDeviceSelect");
        const telSelect = document.getElementById("telemetryDeviceSelect");
        const expSelect = document.getElementById("exportDeviceSelect");

        const optionsHtml = pairedDevices.length === 0 
            ? `<option value="">No paired devices available</option>`
            : pairedDevices.map(d => `<option value="${escapeHtml(d.device_id)}">${escapeHtml(d.device_name || d.device_id)} (${escapeHtml(d.model || 'Android')})</option>`).join("");

        monSelect.innerHTML = optionsHtml;
        telSelect.innerHTML = optionsHtml;
        expSelect.innerHTML = `<option value="">All Devices</option>` + pairedDevices.map(d => `<option value="${escapeHtml(d.device_id)}">${escapeHtml(d.device_name || d.device_id)}</option>`).join("");

        if (pairedDevices.length > 0) {
            if (!selectedTelemetryDevice) selectedTelemetryDevice = pairedDevices[0].device_id;
            if (!selectedMonitoringDevice) selectedMonitoringDevice = pairedDevices[0].device_id;
            telSelect.value = selectedTelemetryDevice;
            monSelect.value = selectedMonitoringDevice;
        }
    }

    async function generatePairingPin() {
        const nameInput = document.getElementById("pairDeviceNameInput").value.trim() || "Authorized Android Device";
        try {
            const res = await fetch(`${API_BASE}/pairing/init`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_name: nameInput })
            });
            if (res.ok) {
                const data = await res.json();
                showPairingPinUI(data.pairing_pin, data.expires_in_seconds);
                loadOverview();
            }
        } catch (err) {
            alert("Pairing initialization failed: " + err.message);
        }
    }

    function showPairingPinUI(pin, seconds) {
        const box = document.getElementById("modalPinBox");
        const display = document.getElementById("modalPinDisplay");
        const countdown = document.getElementById("modalPinCountdown");

        box.style.display = "block";
        display.textContent = pin;

        let rem = seconds;
        if (pinInterval) clearInterval(pinInterval);
        pinInterval = setInterval(() => {
            rem--;
            const mins = Math.floor(rem / 60);
            const secs = rem % 60;
            countdown.textContent = `Valid for ${mins}:${secs < 10 ? '0' : ''}${secs}`;
            if (rem <= 0) {
                clearInterval(pinInterval);
                box.style.display = "none";
            }
        }, 1000);
    }

    window.revokeDeviceAccess = async function (deviceId) {
        if (!confirm(`Are you sure you want to revoke authorization for device: ${deviceId}?\nThis will disconnect live sessions immediately.`)) {
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/pairing/revoke/${encodeURIComponent(deviceId)}`, {
                method: "POST"
            });
            if (res.ok) {
                await loadDevices();
                await loadOverview();
                await loadMonitoring();
                alert(`Device ${deviceId} revoked successfully.`);
            }
        } catch (err) {
            alert("Failed to revoke device: " + err.message);
        }
    };

    window.viewDeviceDetails = function (deviceId) {
        const d = cachedDevices.find(x => x.device_id === deviceId);
        if (!d) return;

        const isOnline = connectedDeviceIds.has(deviceId);
        deviceDetailsContent.innerHTML = `
            <div><strong>Device Label:</strong> ${escapeHtml(d.device_name || "None")}</div>
            <div><strong>Device ID:</strong> <code>${escapeHtml(d.device_id)}</code></div>
            <div><strong>Hardware Model:</strong> ${escapeHtml(d.model || "Unknown")}</div>
            <div><strong>OS Version:</strong> ${escapeHtml(d.os_version || "Android")}</div>
            <div><strong>Pairing Status:</strong> <span class="badge ${d.status === 'paired' ? 'badge-paired' : 'badge-revoked'}">${escapeHtml(d.status.toUpperCase())}</span></div>
            <div><strong>WebSocket Connection:</strong> ${isOnline ? '<span class="badge badge-paired">CONNECTED (Active Socket)</span>' : '<span class="badge badge-stopped">OFFLINE</span>'}</div>
            <div><strong>Registered Date:</strong> ${formatTimestamp(d.created_at)}</div>
            <div><strong>Last Seen:</strong> ${formatTimestamp(d.last_seen_at)}</div>
        `;
        document.getElementById("deviceDetailsModal").classList.add("active");
    };

    window.filterEventsForDevice = function (deviceId) {
        switchTab("tab-events");
        const filterSelect = document.getElementById("eventsFilterType");
        loadSecurityEvents(deviceId);
    };

    // MODULE 3: Monitoring Controls & Screen Viewer
    function setupMonitoringControls() {
        document.getElementById("btnStartMonitoring").addEventListener("click", requestStartStream);
        document.getElementById("btnStopMonitoring").addEventListener("click", executeStopStream);
        document.getElementById("btnBannerEmergencyStop").addEventListener("click", executeStopStream);

        document.getElementById("monitoringDeviceSelect").addEventListener("change", (e) => {
            selectedMonitoringDevice = e.target.value;
        });
    }

    async function loadMonitoring() {
        try {
            const res = await fetch(`${API_BASE}/monitoring/sessions`);
            if (res.ok) {
                const sessions = await res.json();
                renderSessionHistory(sessions);
            }
        } catch (err) {
            console.error("Failed to load sessions", err);
        }
    }

    function renderSessionHistory(sessions) {
        const container = document.getElementById("monitoringHistoryList");
        if (!sessions || sessions.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding: 1rem;">No prior sessions recorded.</div>`;
            return;
        }

        container.innerHTML = sessions.map(s => `
            <div style="padding: 0.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div><strong>${escapeHtml(s.device_name || s.device_id)}</strong></div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${formatTimestamp(s.started_at)}</div>
                </div>
                <span class="badge ${s.status === 'active' ? 'badge-active' : 'badge-stopped'}">${s.status.toUpperCase()}</span>
            </div>
        `).join("");
    }

    async function requestStartStream() {
        const devId = document.getElementById("monitoringDeviceSelect").value;
        if (!devId) {
            alert("Please select a paired device first.");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/monitoring/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: devId, session_type: "screen_share" })
            });
            const data = await res.json();
            if (data.status === "pending_agent_connection") {
                alert(`Agent Offline: ${data.message}`);
            } else if (data.status === "started") {
                updateSessionStateUI("active", devId, data.session_id);
            }
        } catch (err) {
            alert("Failed to start session: " + err.message);
        }
    }

    async function executeStopStream() {
        try {
            await fetch(`${API_BASE}/monitoring/stop`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: selectedMonitoringDevice })
            });
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ event: "COMMAND_STOP_STREAM", device_id: selectedMonitoringDevice }));
            }
            updateSessionStateUI("stopped", selectedMonitoringDevice);
            resetScreenStreamView("Monitoring Stopped by Operator");
            loadMonitoring();
            loadOverview();
        } catch (err) {
            console.error("Stop command failed", err);
        }
    }

    function updateSessionStateUI(state, deviceId, sessionId = "") {
        const badge = document.getElementById("monitoringSessionStatusBadge");
        const sidSpan = document.getElementById("monitoringSessionId");
        const startedSpan = document.getElementById("monitoringSessionStarted");
        const endedSpan = document.getElementById("monitoringSessionEnded");

        if (state === "active") {
            badge.className = "badge badge-active";
            badge.textContent = "ACTIVE";
            activeBanner.classList.add("visible");
            sidSpan.textContent = sessionId || "active_session";
            startedSpan.textContent = new Date().toLocaleTimeString();
            endedSpan.textContent = "In Progress";
        } else {
            badge.className = "badge badge-stopped";
            badge.textContent = "STOPPED";
            activeBanner.classList.remove("visible");
            endedSpan.textContent = new Date().toLocaleTimeString();
        }
    }

    function renderScreenFrame(base64Jpeg, deviceId) {
        if (!base64Jpeg) return;
        activeBanner.classList.add("visible");
        viewportPlaceholder.style.display = "none";
        screenCanvas.style.display = "block";
        viewportStatusText.textContent = `LIVE STREAMING: ${deviceId}`;

        const img = new Image();
        img.onload = () => {
            screenCanvas.width = img.width;
            screenCanvas.height = img.height;
            canvasCtx.drawImage(img, 0, 0);
            viewportResolutionBadge.textContent = `${img.width}x${img.height} @ LIVE`;
        };
        img.src = `data:image/jpeg;base64,${base64Jpeg}`;
    }

    function resetScreenStreamView(statusMessage = "Waiting for Authorized Stream") {
        viewportPlaceholder.style.display = "block";
        screenCanvas.style.display = "none";
        viewportStatusText.textContent = `STATUS: ${statusMessage.toUpperCase()}`;
        viewportResolutionBadge.textContent = "0x0 @ 0 FPS";
    }

    // MODULE 4: Telemetry
    function setupTelemetryListener() {
        document.getElementById("telemetryDeviceSelect").addEventListener("change", (e) => {
            selectedTelemetryDevice = e.target.value;
            loadTelemetryForSelected();
        });
    }

    async function loadTelemetryForSelected() {
        setupTelemetryListener();
        const devId = document.getElementById("telemetryDeviceSelect").value || selectedTelemetryDevice;
        if (!devId) {
            renderUnavailableTelemetry("No paired device selected");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/telemetry/latest/${encodeURIComponent(devId)}`);
            if (res.ok) {
                const body = await res.json();
                if (body.available && body.data) {
                    renderTelemetryValues(body.data);
                } else {
                    renderUnavailableTelemetry(body.message);
                }
            }
        } catch (err) {
            console.error("Failed to load telemetry", err);
            renderUnavailableTelemetry("Error fetching telemetry");
        }
    }

    function handleLiveTelemetry(data) {
        if (data.device_id === selectedTelemetryDevice) {
            renderTelemetryValues(data);
        }
    }

    function renderTelemetryValues(d) {
        document.getElementById("telemetryUnavailableBox").style.display = "none";
        document.getElementById("telBatteryValue").innerHTML = `${d.battery_level !== undefined ? d.battery_level : '--'} <span style="font-size: 1rem; font-weight: normal;">%</span>`;
        document.getElementById("telChargingValue").textContent = d.is_charging ? "Charging (Connected)" : "On Battery";
        document.getElementById("telNetworkValue").textContent = d.network_type || "Active Interface";
        document.getElementById("telNetworkSub").textContent = "Live Connectivity";
        document.getElementById("telCpuValue").innerHTML = `${d.cpu_usage !== undefined ? d.cpu_usage.toFixed(1) : '--'} <span style="font-size: 1rem; font-weight: normal;">%</span>`;
        document.getElementById("telRamValue").textContent = `RAM: ${d.ram_usage_mb !== undefined ? d.ram_usage_mb.toFixed(0) + ' MB' : 'Unavailable'}`;
        document.getElementById("telTimestampValue").textContent = formatTimestamp(d.recorded_at);
        document.getElementById("telTimestampSub").textContent = "Telemetry Ingestion Verified";
    }

    function renderUnavailableTelemetry(msg) {
        document.getElementById("telemetryUnavailableBox").style.display = "block";
        document.getElementById("telemetryUnavailableMessage").textContent = msg || "Unavailable — Waiting for telemetry report from Android agent.";
        document.getElementById("telBatteryValue").innerHTML = `-- <span style="font-size: 1rem; font-weight: normal;">%</span>`;
        document.getElementById("telChargingValue").textContent = "Unavailable";
        document.getElementById("telNetworkValue").textContent = "--";
        document.getElementById("telNetworkSub").textContent = "Unavailable";
        document.getElementById("telCpuValue").innerHTML = `-- <span style="font-size: 1rem; font-weight: normal;">%</span>`;
        document.getElementById("telRamValue").textContent = "RAM: Unavailable";
        document.getElementById("telTimestampValue").textContent = "--";
        document.getElementById("telTimestampSub").textContent = "Waiting for device report";
    }

    // MODULE 5: Typing Lab Sandbox
    let typingStartTime = null;
    let typingTimerInterval = null;
    let keystrokeHistory = [];
    let lastKeyUpTime = null;
    let totalErrors = 0;

    function setupTypingLab() {
        const input = document.getElementById("typingTestInput");
        const resetBtn = document.getElementById("btnResetTypingTest");

        input.addEventListener("keydown", handleTypingKeyDown);
        input.addEventListener("keyup", handleTypingKeyUp);
        input.addEventListener("input", handleTypingInput);
        resetBtn.addEventListener("click", resetTypingTest);

        loadTypingAuditLog();
    }

    function handleTypingKeyDown(e) {
        const now = performance.now();
        if (!typingStartTime) {
            typingStartTime = now;
            startTypingCountdown(30);
        }

        // Measure flight time (time from previous keyup to this keydown)
        let flightTime = 0;
        if (lastKeyUpTime) {
            flightTime = Math.max(0, now - lastKeyUpTime);
        }

        e.target.dataset.currentKeyDown = now.toString();
        e.target.dataset.lastFlight = flightTime.toString();
    }

    function handleTypingKeyUp(e) {
        const now = performance.now();
        lastKeyUpTime = now;
        const downTime = parseFloat(e.target.dataset.currentKeyDown || now);
        const flightTime = parseFloat(e.target.dataset.lastFlight || 0);
        const holdTime = Math.max(0, now - downTime);

        keystrokeHistory.push({
            key: e.key,
            flightTime: flightTime,
            holdTime: holdTime
        });

        updateTypingLiveMetrics();
    }

    function handleTypingInput(e) {
        const prompt = document.getElementById("typingBenchmarkPrompt").innerText.trim();
        const typed = e.target.value;

        totalErrors = 0;
        for (let i = 0; i < typed.length; i++) {
            if (i >= prompt.length || typed[i] !== prompt[i]) {
                totalErrors++;
            }
        }
        updateTypingLiveMetrics();
    }

    function updateTypingLiveMetrics() {
        const input = document.getElementById("typingTestInput");
        const typed = input.value;
        const totalKeys = keystrokeHistory.length;
        const elapsedMinutes = typingStartTime ? (performance.now() - typingStartTime) / 60000 : 0.001;

        // WPM calculation: (keystrokes / 5) / elapsedMinutes
        const wpm = elapsedMinutes > 0 ? (typed.length / 5) / elapsedMinutes : 0;
        const accuracy = typed.length > 0 ? Math.max(0, ((typed.length - totalErrors) / typed.length) * 100) : 100;

        // Flight & Hold times
        const avgFlight = keystrokeHistory.length > 0 
            ? keystrokeHistory.reduce((acc, k) => acc + k.flightTime, 0) / keystrokeHistory.length 
            : 0;
        const avgHold = keystrokeHistory.length > 0 
            ? keystrokeHistory.reduce((acc, k) => acc + k.holdTime, 0) / keystrokeHistory.length 
            : 0;

        document.getElementById("liveTypingWpm").innerHTML = `${wpm.toFixed(1)} <span style="font-size: 0.9rem; font-weight: normal;">WPM</span>`;
        document.getElementById("liveTypingAccuracy").innerHTML = `${accuracy.toFixed(1)} <span style="font-size: 0.9rem; font-weight: normal;">%</span>`;
        document.getElementById("liveTypingFlight").innerHTML = `${avgFlight.toFixed(0)} <span style="font-size: 0.9rem; font-weight: normal;">ms</span>`;
        document.getElementById("liveTypingHold").innerHTML = `${avgHold.toFixed(0)} <span style="font-size: 0.9rem; font-weight: normal;">ms</span>`;

        document.getElementById("statTotalKeys").textContent = totalKeys;
        document.getElementById("statCorrectKeys").textContent = Math.max(0, typed.length - totalErrors);
        document.getElementById("statErrorKeys").textContent = totalErrors;
    }

    function startTypingCountdown(seconds) {
        let rem = seconds;
        const timerSpan = document.getElementById("typingTimer");
        if (typingTimerInterval) clearInterval(typingTimerInterval);

        typingTimerInterval = setInterval(() => {
            rem--;
            timerSpan.textContent = `${rem}s`;
            if (rem <= 0) {
                clearInterval(typingTimerInterval);
                document.getElementById("typingTestInput").disabled = true;
                timerSpan.textContent = "COMPLETED";
            }
        }, 1000);
    }

    function resetTypingTest() {
        if (typingTimerInterval) clearInterval(typingTimerInterval);
        typingStartTime = null;
        lastKeyUpTime = null;
        keystrokeHistory = [];
        totalErrors = 0;

        const input = document.getElementById("typingTestInput");
        input.disabled = false;
        input.value = "";
        document.getElementById("typingTimer").textContent = "30s";

        document.getElementById("liveTypingWpm").innerHTML = `0.0 <span style="font-size: 0.9rem; font-weight: normal;">WPM</span>`;
        document.getElementById("liveTypingAccuracy").innerHTML = `100 <span style="font-size: 0.9rem; font-weight: normal;">%</span>`;
        document.getElementById("liveTypingFlight").innerHTML = `0 <span style="font-size: 0.9rem; font-weight: normal;">ms</span>`;
        document.getElementById("liveTypingHold").innerHTML = `0 <span style="font-size: 0.9rem; font-weight: normal;">ms</span>`;
        document.getElementById("statTotalKeys").textContent = "0";
        document.getElementById("statCorrectKeys").textContent = "0";
        document.getElementById("statErrorKeys").textContent = "0";
    }

    async function loadTypingAuditLog() {
        const tbody = document.getElementById("typingAuditLogBody");
        const devId = selectedTelemetryDevice || (cachedDevices.length > 0 ? cachedDevices[0].device_id : "");
        if (!devId) {
            tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No typing benchmarks recorded yet.</td></tr>`;
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/typing/benchmarks/${encodeURIComponent(devId)}`);
            if (res.ok) {
                const logs = await res.json();
                if (!logs || logs.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No typing benchmarks recorded for device ${escapeHtml(devId)}.</td></tr>`;
                    return;
                }

                tbody.innerHTML = logs.map(l => `
                    <tr>
                        <td>${formatTimestamp(l.recorded_at)}</td>
                        <td><code>${escapeHtml(l.device_id || devId)}</code></td>
                        <td><code>${escapeHtml(l.test_prompt_id || "default")}</code></td>
                        <td><strong>${l.wpm.toFixed(1)} WPM</strong></td>
                        <td>${l.accuracy_percent.toFixed(1)}%</td>
                        <td>${l.avg_flight_time_ms.toFixed(0)} ms</td>
                        <td>${l.avg_hold_time_ms.toFixed(0)} ms</td>
                        <td>${l.total_keystrokes} / ${l.error_count}</td>
                    </tr>
                `).join("");
            }
        } catch (err) {
            console.error("Failed to load typing audit log", err);
        }
    }

    // MODULE 6: Security Events
    async function loadSecurityEvents(filterDeviceId = "") {
        const filterType = document.getElementById("eventsFilterType").value;
        const tbody = document.getElementById("eventsFullTableBody");

        let url = `${API_BASE}/events?limit=100`;
        if (filterDeviceId) url += `&device_id=${encodeURIComponent(filterDeviceId)}`;

        try {
            const res = await fetch(url);
            if (res.ok) {
                let events = await res.json();
                if (filterType) {
                    events = events.filter(e => e.event_type === filterType);
                }

                if (!events || events.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No security events found.</td></tr>`;
                    return;
                }

                tbody.innerHTML = events.map(e => `
                    <tr>
                        <td><code>#${e.id}</code></td>
                        <td>${formatTimestamp(e.event_timestamp)}</td>
                        <td><code>${escapeHtml(e.device_id || "System")}</code></td>
                        <td><strong>${escapeHtml(e.event_type)}</strong></td>
                        <td><code>${escapeHtml(e.session_id || "—")}</code></td>
                        <td><span class="badge ${getStatusBadgeClass(e.event_status)}">${escapeHtml(e.event_status)}</span></td>
                        <td>${escapeHtml(e.details || "—")}</td>
                    </tr>
                `).join("");
            }
        } catch (err) {
            console.error("Failed to load events", err);
        }
    }

    document.getElementById("btnRefreshOverview").addEventListener("click", loadOverview);
    document.getElementById("btnRefreshEvents").addEventListener("click", () => loadSecurityEvents());
    document.getElementById("eventsFilterType").addEventListener("change", () => loadSecurityEvents());

    // MODULE 7: Reports & Exports
    function setupExportControls() {
        document.getElementById("btnDownloadExport").addEventListener("click", () => {
            const fmt = document.getElementById("exportFormatSelect").value;
            const devId = document.getElementById("exportDeviceSelect").value;

            let url = `${API_BASE}/events/export?format=${encodeURIComponent(fmt)}`;
            if (devId) url += `&device_id=${encodeURIComponent(devId)}`;

            // Trigger browser download via clean anchor click
            const a = document.createElement("a");
            a.href = url;
            a.download = "";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
    }

    // Utilities
    function formatTimestamp(isoStr) {
        if (!isoStr) return "Never";
        try {
            const d = new Date(isoStr);
            return isNaN(d.getTime()) ? isoStr : d.toLocaleString();
        } catch (e) {
            return isoStr;
        }
    }

    function getStatusBadgeClass(status) {
        if (!status) return "badge-stopped";
        const s = status.toUpperCase();
        if (s === "SUCCESS" || s === "PAIRED" || s === "ACTIVE") return "badge-paired";
        if (s === "REVOKED" || s === "TERMINATED" || s === "STOPPED") return "badge-revoked";
        return "badge-pending";
    }

    function escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    window.addEventListener("DOMContentLoaded", init);
})();
