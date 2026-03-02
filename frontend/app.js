const API_BASE = 'http://34.163.202.97:8000/api';
const WS_BASE = 'ws://34.163.202.97:8000/ws';

let map = null;
let currentMarker = null;
let geofenceCircles = [];
let websocket = null;
let currentPatientId = null;
let autoRefreshInterval = null;
let patients = [];

function initMap() {
    if (!map) {
        map = L.map('map').setView([41.3851, 2.1734], 13);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap, © CartoDB',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
    }
}

async function loadPatients() {
    try {
        const response = await fetch(`${API_BASE}/patients`);
        patients = await response.json();

        const listDiv = document.getElementById('patient-list');

        if (patients.length === 0) {
            listDiv.innerHTML = `
                <div class="empty-state" style="padding: 2rem 1rem;">
                    <div class="empty-icon">👤</div>
                    <div class="empty-text">No patients yet.<br>Add your first patient.</div>
                </div>
            `;
            return;
        }

        listDiv.innerHTML = patients.map(patient => `
            <div class="patient-item ${currentPatientId === patient.id ? 'active' : ''}" onclick="selectPatient(${patient.id})">
                <div class="patient-avatar">${patient.full_name.charAt(0).toUpperCase()}</div>
                <div class="patient-info">
                    <div class="patient-name">${patient.full_name}</div>
                    <div class="patient-status">
                        <div class="status-dot" style="background: #10B981;"></div>
                        <span>Active</span>
                    </div>
                </div>
                <button class="patient-delete" data-patient-id="${patient.id}" title="Delete patient">
                    ×
                </button>
            </div>
        `).join('');

        // Add event listeners for delete buttons
        document.querySelectorAll('.patient-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const patientId = parseInt(btn.getAttribute('data-patient-id'));
                await deletePatient(patientId);
            });
        });

    } catch (error) {
        console.error('Failed to load patients:', error);
        showNotification('Failed to load patients. Make sure the backend is running.', 'danger');
    }
}

async function selectPatient(patientId) {
    currentPatientId = patientId;

    if (websocket) {
        websocket.close();
    }

    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }

    // Update UI
    document.getElementById('no-patient-state').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
    document.getElementById('update-btn').style.display = 'inline-flex';
    document.getElementById('header-status-badge').style.display = 'inline-flex';

    // Update notification badge if there are alerts
    updateNotificationBadge();

    // Update sidebar selection
    loadPatients();

    // Initialize map
    initMap();

    // Load data
    await loadPatientDetails(patientId);
    await monitorPatient();

    // Connect WebSocket
    connectWebSocket(patientId);

    // Auto-refresh every 30 seconds
    autoRefreshInterval = setInterval(() => {
        monitorPatient();
    }, 30000);
}

async function loadPatientDetails(patientId) {
    try {
        const response = await fetch(`${API_BASE}/patients/${patientId}`);
        const patient = await response.json();

        displayGeofences(patient.geofences);
        displayAlerts(patient.recent_alerts);
    } catch (error) {
        console.error('Failed to load patient details:', error);
    }
}

async function monitorPatient() {
    if (!currentPatientId) return;

    try {
        const response = await fetch(`${API_BASE}/monitor`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patient_id: currentPatientId })
        });

        const data = await response.json();

        console.log('🔍 Response status:', response.status);
        console.log('🔍 Response ok:', response.ok);
        console.log('🔍 Response data:', data);

        // Check if response is successful
        if (!response.ok) {
            // API returned an error (device offline, unregistered, etc.)
            console.warn('⚠️  API Error - Status:', response.status);
            console.warn('⚠️  API Error - Data:', data.detail || data);

            if (response.status === 500 || response.status === 503) {
                // Device is offline or unregistered
                console.log('📵 Calling showDeviceOffline()');
                showDeviceOffline(data.detail || 'Device is offline or unreachable');
            } else {
                console.log('🔔 Calling showNotification()');
                showNotification(data.detail || 'Failed to update patient status', 'danger');
            }
            return;
        }

        updateDashboard(data);
    } catch (error) {
        console.error('Failed to monitor patient:', error);
        showNotification('Failed to update patient status', 'danger');
    }
}

function updateDashboard(data) {
    console.log('📊 Updating dashboard with data:', data);

    const { location, device_status, sim_swap_info, anomaly_analysis } = data;

    console.log('📍 Location:', location);
    console.log('📱 Device:', device_status);

    // Safety check - ensure all required data exists
    if (!location || !device_status || !anomaly_analysis) {
        console.error('❌ Missing required data in response:', data);
        showNotification('Incomplete data received from server', 'danger');
        return;
    }

    updateMap(location);

    // Update Risk Score
    const riskLevel = anomaly_analysis.risk_level;
    const riskScore = Math.round(anomaly_analysis.anomaly_score);

    const riskCard = document.getElementById('risk-card');
    if (riskCard) {
        riskCard.className = `risk-score-card ${riskLevel}`;
    }

    const riskScoreEl = document.getElementById('risk-score');
    if (riskScoreEl) {
        riskScoreEl.textContent = riskScore;
        console.log('✅ Updated risk-score:', riskScore);
    }

    // Note: risk-label is static text, no need to update

    const statusLabels = {
        low: 'All Clear',
        medium: 'Minor Concerns',
        high: 'Attention Needed',
        critical: 'Critical Alert'
    };

    const riskStatusEl = document.getElementById('risk-status');
    if (riskStatusEl) {
        riskStatusEl.textContent = statusLabels[riskLevel] || 'Monitoring';
        console.log('✅ Updated risk-status:', statusLabels[riskLevel]);
    }

    // Update header status badge
    const badge = document.getElementById('header-status-badge');
    const badgeText = document.getElementById('header-status-text');
    badge.className = 'status-badge';

    if (riskLevel === 'critical' || riskLevel === 'high') {
        badge.classList.add('danger');
        badgeText.textContent = `${statusLabels[riskLevel]}`;
    } else if (riskLevel === 'medium') {
        badge.classList.add('warning');
        badgeText.textContent = statusLabels[riskLevel];
    } else {
        badge.classList.add('success');
        badgeText.textContent = 'All Clear';
    }

    // Update Location
    const lat = location.latitude.toFixed(4);
    const lng = location.longitude.toFixed(4);
    const locationStatusEl = document.getElementById('location-status');
    if (locationStatusEl) {
        locationStatusEl.textContent = `${lat}°N, ${lng}°E`;
        console.log('✅ Updated location-status:', locationStatusEl.textContent);
    } else {
        console.error('❌ Element location-status not found!');
    }

    const locationTime = new Date(location.timestamp).toLocaleTimeString();
    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = `Updated: ${locationTime}`;
        console.log('✅ Updated last-update:', lastUpdateEl.textContent);
    }

    // Update Device
    const deviceConnected = device_status.connected ? 'Online' : 'Offline';
    const deviceIcon = device_status.connected ? '✓' : '✗';
    const deviceStatusEl = document.getElementById('device-status');
    if (deviceStatusEl) {
        deviceStatusEl.textContent = `${deviceIcon} ${deviceConnected}`;
        console.log('✅ Updated device-status:', deviceStatusEl.textContent);
    } else {
        console.error('❌ Element device-status not found!');
    }

    const networkType = device_status.network_type || 'Unknown';
    const networkTypeEl = document.getElementById('network-type');
    if (networkTypeEl) {
        networkTypeEl.textContent = `Network: ${networkType}`;
        console.log('✅ Updated network-type:', networkTypeEl.textContent);
    }

    // Update Battery
    const batteryLevel = device_status.battery_level || 0;
    const batteryIcon = batteryLevel > 80 ? '🔋' : batteryLevel > 20 ? '🔋' : '🪫';
    const batteryLevelEl = document.getElementById('battery-level');
    if (batteryLevelEl) {
        batteryLevelEl.textContent = `${batteryIcon} ${batteryLevel}%`;
        console.log('✅ Updated battery-level:', batteryLevelEl.textContent);
    } else {
        console.error('❌ Element battery-level not found!');
    }

    const signalStrength = device_status.signal_strength || 0;
    const signalIcon = signalStrength > 70 ? '📶' : signalStrength > 40 ? '📶' : '📶';
    const signalStrengthEl = document.getElementById('signal-strength');
    if (signalStrengthEl) {
        signalStrengthEl.textContent = `${signalIcon} ${signalStrength}%`;
        console.log('✅ Updated signal-strength:', signalStrengthEl.textContent);
    }

    // Update Risk Factors
    const riskFactorsDiv = document.getElementById('risk-factors');
    if (anomaly_analysis.risk_factors.length > 0) {
        riskFactorsDiv.innerHTML = `<div class="info-list">` + anomaly_analysis.risk_factors.map(factor => {
            const itemClass = riskLevel === 'critical' || riskLevel === 'high' ? 'danger' :
                            riskLevel === 'medium' ? 'warning' : 'success';
            const icon = riskLevel === 'critical' ? '🚨' : riskLevel === 'high' ? '⚠️' :
                        riskLevel === 'medium' ? '⚠️' : '✓';

            return `
                <div class="info-item ${itemClass}">
                    <div class="info-item-icon">${icon}</div>
                    <div>${factor}</div>
                </div>
            `;
        }).join('') + `</div>`;
    } else {
        riskFactorsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✅</div>
                <div class="empty-text">No risk factors detected</div>
            </div>
        `;
    }

    // Update Recommendations
    const recommendationsDiv = document.getElementById('recommendations');
    if (anomaly_analysis.recommendations.length > 0) {
        recommendationsDiv.innerHTML = `<div class="info-list">` + anomaly_analysis.recommendations.map(rec => {
            const itemClass = rec.includes('IMMEDIATE') || rec.includes('🚨') ? 'danger' :
                            rec.includes('⚠️') ? 'warning' : 'success';
            const icon = rec.includes('IMMEDIATE') || rec.includes('🚨') ? '🚨' :
                        rec.includes('⚠️') ? '💡' : '✅';

            return `
                <div class="info-item ${itemClass}">
                    <div class="info-item-icon">${icon}</div>
                    <div>${rec}</div>
                </div>
            `;
        }).join('') + `</div>`;
    } else {
        recommendationsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✅</div>
                <div class="empty-text">No recommendations</div>
            </div>
        `;
    }

    // Show alert banner for high/critical risks
    if (riskLevel === 'critical' || riskLevel === 'high') {
        showAlert(
            anomaly_analysis.risk_factors[0],
            riskLevel === 'critical' ? 'danger' : 'warning'
        );
    } else {
        hideAlert();
    }

    // Log QoS session
    if (anomaly_analysis.qos_session) {
        console.log('🚀 Emergency QoS activated:', anomaly_analysis.qos_session);
        showNotification('Emergency network priority activated', 'success');
    }

    // Update AI Insights (Gemini)
    const aiInsightsFloat = document.getElementById('ai-insights-float');
    const aiInsightsContent = document.getElementById('ai-insights-content');

    if (anomaly_analysis.ai_insights && anomaly_analysis.ai_insights.trim() !== '') {
        // Show the floating AI insights panel
        aiInsightsFloat.style.display = 'block';

        // Check if it's an error message
        const isError = anomaly_analysis.ai_insights.includes('Unable to generate') ||
                       anomaly_analysis.ai_insights.includes('AI analysis unavailable');

        if (isError) {
            aiInsightsContent.innerHTML = `
                <div style="display: flex; align-items: start; gap: 1rem; padding: 0.75rem; background: #FEF2F2; border-radius: 8px; border-left: 4px solid #EF4444;">
                    <div style="font-size: 1.5rem;">⚠️</div>
                    <div>
                        <div style="font-weight: 600; color: #DC2626; margin-bottom: 0.25rem;">AI Analysis Temporarily Unavailable</div>
                        <div style="font-size: 0.875rem; color: #991B1B;">${anomaly_analysis.ai_insights}</div>
                    </div>
                </div>
            `;
        } else {
            // Display the Gemini-generated insights
            aiInsightsContent.innerHTML = `
                <div style="display: flex; align-items: start; gap: 1rem;">
                    <div style="font-size: 2rem; flex-shrink: 0;">🤖</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #4285F4; margin-bottom: 0.5rem; font-size: 1rem;">
                            🧠 Google Gemini AI Analysis
                        </div>
                        <div style="color: #374151; line-height: 1.7;">
                            ${anomaly_analysis.ai_insights}
                        </div>
                        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #E5E7EB; font-size: 0.8125rem; color: #6B7280; display: flex; align-items: center; gap: 0.5rem;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="opacity: 0.7;">
                                <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V7.89l7-3.11v8.21z"/>
                            </svg>
                            Generated by Google Gemini 2.5 Flash AI • Real-time analysis
                        </div>
                    </div>
                </div>
            `;
        }
    } else if (riskLevel === 'medium' || riskLevel === 'high' || riskLevel === 'critical') {
        // Show card but indicate AI is analyzing
        aiInsightsCard.style.display = 'block';
        aiInsightsContent.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; padding: 2rem; color: #6B7280;">
                <div class="loading-spinner"></div>
                <div>Gemini AI is analyzing the situation...</div>
            </div>
        `;
    } else {
        // Hide for low risk scenarios
        aiInsightsCard.style.display = 'none';
    }

    // Update quick metrics view
    updateQuickMetrics(data);
}

function updateMap(location) {
    if (!map) return;

    const lat = location.latitude;
    const lng = location.longitude;

    if (currentMarker) {
        map.removeLayer(currentMarker);
    }

    const customIcon = L.divIcon({
        className: 'custom-marker',
        html: `
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #3B82F6, #2563EB);
                border: 3px solid white;
                border-radius: 50%;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
            ">📍</div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });

    currentMarker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
    currentMarker.bindPopup(`
        <div style="font-family: Inter, sans-serif; padding: 0.5rem;">
            <div style="font-weight: 600; font-size: 0.9375rem; margin-bottom: 0.5rem;">📍 Nokia Location API</div>
            <div style="font-size: 0.8125rem; color: #6B7280; line-height: 1.5;">
                <div><strong>Lat:</strong> ${lat.toFixed(6)}</div>
                <div><strong>Lng:</strong> ${lng.toFixed(6)}</div>
                <div><strong>Accuracy:</strong> ±${location.accuracy}m</div>
            </div>
        </div>
    `).openPopup();

    map.setView([lat, lng], 15);

    // Update coordinates display below map
    const coordsElement = document.getElementById('map-lat-lng');
    if (coordsElement) {
        coordsElement.textContent = `${lat.toFixed(6)}°N, ${lng.toFixed(6)}°E`;
    }
}

function displayGeofences(geofences) {
    if (!map) return;

    geofenceCircles.forEach(circle => map.removeLayer(circle));
    geofenceCircles = [];

    const listDiv = document.getElementById('geofences-list');

    if (geofences.length === 0) {
        listDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🏠</div>
                <div class="empty-text">No safe zones</div>
            </div>
        `;
        return;
    }

    listDiv.innerHTML = geofences.map(geofence => `
        <div style="
            padding: 0.75rem;
            background: var(--color-success-bg);
            border: 1px solid var(--color-success-light);
            border-radius: 6px;
            margin-bottom: 0.5rem;
        ">
            <div style="font-weight: 600; font-size: 0.875rem; color: var(--color-success); margin-bottom: 0.25rem;">
                🏠 ${geofence.name}
            </div>
            <div style="font-size: 0.75rem; color: var(--color-text-secondary);">
                Radius: ${geofence.radius_meters}m
            </div>
        </div>
    `).join('');

    geofences.forEach(geofence => {
        const circle = L.circle([geofence.latitude, geofence.longitude], {
            color: '#10B981',
            fillColor: '#10B981',
            fillOpacity: 0.15,
            weight: 2,
            radius: geofence.radius_meters
        }).addTo(map);

        circle.bindPopup(`
            <div style="font-family: Inter, sans-serif; padding: 0.5rem;">
                <div style="font-weight: 600; font-size: 0.9375rem; margin-bottom: 0.25rem; color: #10B981;">
                    🏠 ${geofence.name}
                </div>
                <div style="font-size: 0.8125rem; color: #6B7280;">Safe Zone</div>
            </div>
        `);
        geofenceCircles.push(circle);
    });
}

function displayAlerts(alerts) {
    const listDiv = document.getElementById('alerts-list');

    if (alerts.length === 0) {
        listDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✅</div>
                <div class="empty-text">No recent alerts</div>
            </div>
        `;
        return;
    }

    listDiv.innerHTML = alerts.map(alert => {
        const severityColors = {
            critical: { bg: 'var(--color-danger-bg)', border: 'var(--color-danger-light)', text: 'var(--color-danger)' },
            high: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning-light)', text: 'var(--color-warning)' },
            medium: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning-light)', text: 'var(--color-warning)' },
            low: { bg: 'var(--color-success-bg)', border: 'var(--color-success-light)', text: 'var(--color-success)' }
        };

        const colors = severityColors[alert.severity] || severityColors.medium;
        const icons = { critical: '🚨', high: '⚠️', medium: '⚠️', low: '✓' };

        return `
            <div style="
                padding: 0.75rem;
                background: ${colors.bg};
                border: 1px solid ${colors.border};
                border-radius: 6px;
                margin-bottom: 0.5rem;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.375rem;">
                    <div style="font-weight: 600; font-size: 0.8125rem; color: ${colors.text}; text-transform: uppercase;">
                        ${icons[alert.severity] || '•'} ${alert.severity}
                    </div>
                    <div style="font-size: 0.6875rem; color: var(--color-text-tertiary);">
                        ${new Date(alert.created_at).toLocaleTimeString()}
                    </div>
                </div>
                <div style="font-size: 0.8125rem; line-height: 1.5; color: ${colors.text};">
                    ${alert.message}
                </div>
            </div>
        `;
    }).join('');
}

function showAlert(message, severity) {
    const banner = document.getElementById('alert-banner');
    const className = severity === 'danger' ? 'alert-banner danger' : 'alert-banner warning';
    const icon = severity === 'danger' ? '🚨' : '⚠️';

    banner.className = className;
    banner.innerHTML = `
        <div style="font-size: 1.25rem;">${icon}</div>
        <div style="flex: 1;">
            <div style="font-weight: 600; font-size: 0.875rem; margin-bottom: 0.25rem;">
                ${severity === 'danger' ? 'Critical Alert' : 'Warning'}
            </div>
            <div style="font-size: 0.875rem; line-height: 1.5;">${message}</div>
        </div>
    `;
    banner.style.display = 'flex';
}

function hideAlert() {
    document.getElementById('alert-banner').style.display = 'none';
}

function showNotification(message, type) {
    // Simple console notification - could be enhanced with toast notifications
    console.log(`[${type.toUpperCase()}]`, message);
}

function showDeviceOffline(errorMessage) {
    console.warn('📵 Device Offline:', errorMessage);

    // Show alert banner with full message
    const fullMessage = `📵 Device Offline: ${errorMessage}`;
    showAlert(fullMessage, 'danger');

    // Update dashboard to show offline state
    const riskScoreEl = document.getElementById('risk-score');
    if (riskScoreEl) {
        riskScoreEl.textContent = '—';
    }

    const riskStatusEl = document.getElementById('risk-status');
    if (riskStatusEl) {
        riskStatusEl.textContent = 'Device Offline';
    }

    const riskCard = document.getElementById('risk-card');
    if (riskCard) {
        riskCard.className = 'risk-score-card low';
    }

    const locationStatusEl = document.getElementById('location-status');
    if (locationStatusEl) {
        locationStatusEl.textContent = 'Offline';
    }

    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = 'Device unreachable';
    }

    const deviceStatusEl = document.getElementById('device-status');
    if (deviceStatusEl) {
        deviceStatusEl.textContent = '✗ Offline';
    }

    const networkTypeEl = document.getElementById('network-type');
    if (networkTypeEl) {
        networkTypeEl.textContent = 'Network: —';
    }

    const batteryLevelEl = document.getElementById('battery-level');
    if (batteryLevelEl) {
        batteryLevelEl.textContent = '—';
    }

    const signalStrengthEl = document.getElementById('signal-strength');
    if (signalStrengthEl) {
        signalStrengthEl.textContent = '—';
    }

    // Update header status badge
    const badge = document.getElementById('header-status-badge');
    const badgeText = document.getElementById('header-status-text');
    if (badge && badgeText) {
        badge.className = 'status-badge danger';
        badgeText.textContent = 'Device Offline';
    }

    // Update connection status indicator
    updateConnectionStatus(false, 'offline');
}

function connectWebSocket(patientId) {
    try {
        websocket = new WebSocket(`${WS_BASE}/patient/${patientId}`);

        websocket.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'location_update') {
                updateDashboard(data);
            }
        };

        websocket.onerror = () => {
            updateConnectionStatus(false, 'error');
        };

        websocket.onclose = () => {
            updateConnectionStatus(false);
        };

        setInterval(() => {
            if (websocket.readyState === WebSocket.OPEN) {
                websocket.send('ping');
            }
        }, 10000);
    } catch (error) {
        console.error('WebSocket connection failed:', error);
        updateConnectionStatus(false, 'error');
    }
}

function updateConnectionStatus(connected, status = 'normal') {
    const sidebarDot = document.getElementById('sidebar-connection-dot');
    const sidebarText = document.getElementById('sidebar-connection-text');

    // Check if elements exist (removed from UI)
    if (!sidebarDot || !sidebarText) return;

    if (connected) {
        sidebarDot.style.background = '#10B981';
        sidebarText.textContent = 'Connected';
    } else if (status === 'error') {
        sidebarDot.style.background = '#EF4444';
        sidebarText.textContent = 'Connection Error';
    } else {
        sidebarDot.style.background = '#F59E0B';
        sidebarText.textContent = 'Disconnected';
    }
}

function showAddPatientModal() {
    document.getElementById('add-patient-modal').style.display = 'flex';
}

function hideAddPatientModal() {
    document.getElementById('add-patient-modal').style.display = 'none';
    document.getElementById('add-patient-form').reset();

    // Reset test toggle
    const toggle = document.getElementById('test-toggle-patient');
    toggle.classList.remove('active');
    toggle.querySelector('span').textContent = 'Fill Test Data';
}

function showAddGeofenceModal() {
    if (!currentPatientId) {
        showNotification('Please select a patient first', 'warning');
        return;
    }

    if (map && currentMarker) {
        const center = currentMarker.getLatLng();
        const latInput = document.querySelector('input[name="latitude"]');
        const lngInput = document.querySelector('input[name="longitude"]');
        latInput.value = center.lat.toFixed(6);
        lngInput.value = center.lng.toFixed(6);
        // Mark as auto-filled so test toggle doesn't clear it
        latInput.dataset.autoFilled = 'true';
        lngInput.dataset.autoFilled = 'true';
    }

    document.getElementById('add-geofence-modal').style.display = 'flex';
}

function hideAddGeofenceModal() {
    const form = document.getElementById('add-geofence-form');
    document.getElementById('add-geofence-modal').style.display = 'none';
    form.reset();

    // Reset auto-filled flags
    delete form.querySelector('input[name="latitude"]').dataset.autoFilled;
    delete form.querySelector('input[name="longitude"]').dataset.autoFilled;

    // Reset test toggle
    const toggle = document.getElementById('test-toggle-geofence');
    toggle.classList.remove('active');
    toggle.querySelector('span').textContent = 'Fill Test Data';
}

// Form submissions
document.getElementById('add-patient-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // Remove empty optional fields (convert empty strings to undefined so they won't be sent)
    Object.keys(data).forEach(key => {
        if (data[key] === '') {
            delete data[key];
        }
    });

    try {
        const response = await fetch(`${API_BASE}/patients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            hideAddPatientModal();
            await loadPatients();
            showNotification('Patient created successfully', 'success');

            // Select the newly created patient
            const newPatient = await response.json();
            if (newPatient.id) {
                await selectPatient(newPatient.id);
            }
        } else {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            showNotification(`Failed to create patient: ${errorData.detail || 'Unknown error'}`, 'danger');
        }
    } catch (error) {
        console.error('Error creating patient:', error);
        showNotification('Failed to create patient', 'danger');
    }
});

document.getElementById('add-geofence-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    data.patient_id = currentPatientId;
    data.radius_meters = parseInt(data.radius_meters);
    data.latitude = parseFloat(data.latitude);
    data.longitude = parseFloat(data.longitude);

    try {
        const response = await fetch(`${API_BASE}/geofences`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            hideAddGeofenceModal();
            await loadPatientDetails(currentPatientId);
            showNotification('Safe zone created successfully', 'success');
        } else {
            showNotification('Failed to create safe zone', 'danger');
        }
    } catch (error) {
        console.error('Error creating geofence:', error);
        showNotification('Failed to create safe zone', 'danger');
    }
});

// Modal backdrop click to close
document.getElementById('add-patient-modal').addEventListener('click', (e) => {
    if (e.target.id === 'add-patient-modal') hideAddPatientModal();
});

document.getElementById('add-geofence-modal').addEventListener('click', (e) => {
    if (e.target.id === 'add-geofence-modal') hideAddGeofenceModal();
});

// Test Data Functions
const testPatients = [
    {
        full_name: 'Maria Rodriguez',
        phone_number: '+34612345678',
        emergency_contact_name: 'John Rodriguez',
        emergency_contact_phone: '+34699887766'
    },
    {
        full_name: 'Antonio García',
        phone_number: '+34623456789',
        emergency_contact_name: 'Carmen García',
        emergency_contact_phone: '+34688776655'
    },
    {
        full_name: 'Isabel Fernández',
        phone_number: '+34634567890',
        emergency_contact_name: 'Miguel Fernández',
        emergency_contact_phone: '+34677665544'
    },
    {
        full_name: 'Manuel López',
        phone_number: '+34645678901',
        emergency_contact_name: 'Ana López',
        emergency_contact_phone: '+34666554433'
    }
];

const testZones = [
    { name: 'Home', lat: 41.3851, lng: 2.1734, radius: 500 },
    { name: 'Hospital del Mar', lat: 41.3865, lng: 2.1965, radius: 200 },
    { name: 'Park', lat: 41.3838, lng: 2.1765, radius: 300 },
    { name: 'Shopping Center', lat: 41.3890, lng: 2.1580, radius: 400 },
    { name: 'Community Center', lat: 41.3825, lng: 2.1800, radius: 250 }
];

let currentTestPatientIndex = 0;
let currentTestZoneIndex = 0;

function toggleTestDataPatient(event) {
    event.preventDefault();
    event.stopPropagation();

    const toggle = document.getElementById('test-toggle-patient');
    const form = document.getElementById('add-patient-form');

    if (toggle.classList.contains('active')) {
        // Clear form
        form.reset();
        toggle.classList.remove('active');
        toggle.querySelector('span').textContent = 'Fill Test Data';
    } else {
        // Fill with test data
        const testData = testPatients[currentTestPatientIndex % testPatients.length];
        currentTestPatientIndex++;

        form.querySelector('input[name="full_name"]').value = testData.full_name;
        form.querySelector('input[name="phone_number"]').value = testData.phone_number;
        form.querySelector('input[name="emergency_contact_name"]').value = testData.emergency_contact_name;
        form.querySelector('input[name="emergency_contact_phone"]').value = testData.emergency_contact_phone;

        toggle.classList.add('active');
        toggle.querySelector('span').textContent = 'Clear Data';
    }
}

function toggleTestDataGeofence(event) {
    event.preventDefault();
    event.stopPropagation();

    const toggle = document.getElementById('test-toggle-geofence');
    const form = document.getElementById('add-geofence-form');

    if (toggle.classList.contains('active')) {
        // Clear form
        const latInput = form.querySelector('input[name="latitude"]');
        const lngInput = form.querySelector('input[name="longitude"]');
        const nameInput = form.querySelector('input[name="name"]');
        const radiusInput = form.querySelector('input[name="radius_meters"]');

        nameInput.value = '';
        // Keep lat/lng if they were auto-filled from current location
        if (!latInput.dataset.autoFilled) {
            latInput.value = '';
            lngInput.value = '';
        }
        radiusInput.value = '500';

        toggle.classList.remove('active');
        toggle.querySelector('span').textContent = 'Fill Test Data';
    } else {
        // Fill with test data
        const testData = testZones[currentTestZoneIndex % testZones.length];
        currentTestZoneIndex++;

        form.querySelector('input[name="name"]').value = testData.name;
        form.querySelector('input[name="latitude"]').value = testData.lat.toFixed(6);
        form.querySelector('input[name="longitude"]').value = testData.lng.toFixed(6);
        form.querySelector('input[name="radius_meters"]').value = testData.radius;

        toggle.classList.add('active');
        toggle.querySelector('span').textContent = 'Clear Data';
    }
}

// Search functionality
let allAlerts = [];
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }
});

function performSearch(query) {
    if (!query.trim()) {
        return;
    }

    query = query.toLowerCase();

    // Search patients
    const matchingPatients = patients.filter(p =>
        p.full_name.toLowerCase().includes(query) ||
        p.phone_number.includes(query)
    );

    // If exact patient match, select it
    if (matchingPatients.length === 1) {
        selectPatient(matchingPatients[0].id);
    } else if (matchingPatients.length > 1) {
        // Highlight matching patients in sidebar
        console.log('Multiple patients match:', matchingPatients);
    }

    // Search could also filter alerts, locations, etc.
}

// Notifications
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (!badge) return;

    // Count unread alerts (would need backend support for "read" status)
    const alertsList = document.getElementById('alerts-list');
    if (alertsList && alertsList.children.length > 0) {
        const alertCount = alertsList.children.length;
        badge.textContent = alertCount;
        badge.style.display = alertCount > 0 ? 'flex' : 'none';
    }
}

function showNotifications() {
    // For now, scroll to alerts section
    const alertsCard = document.querySelector('#alerts-list').closest('.card');
    if (alertsCard) {
        alertsCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        alertsCard.style.animation = 'pulse 0.5s';
    }
}

// Export data functionality
async function exportData() {
    if (!currentPatientId) {
        alert('Please select a patient first');
        return;
    }

    try {
        const patient = patients.find(p => p.id === currentPatientId);
        const response = await fetch(`${API_BASE}/patients/${currentPatientId}`);
        const data = await response.json();

        // Create CSV export
        const csvContent = `CarePulse Patient Report - ${new Date().toLocaleString()}\n\n` +
            `Patient: ${data.full_name}\n` +
            `Phone: ${data.phone_number}\n` +
            `Emergency Contact: ${data.emergency_contact_name || 'N/A'} (${data.emergency_contact_phone || 'N/A'})\n\n` +
            `Recent Alerts:\n` +
            data.recent_alerts.map(a =>
                `${new Date(a.created_at).toLocaleString()},${a.severity},${a.message}`
            ).join('\n') + '\n\n' +
            `Safe Zones:\n` +
            data.geofences.map(g =>
                `${g.name},${g.latitude},${g.longitude},${g.radius_meters}m`
            ).join('\n');

        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `carepulse-${patient.full_name.replace(/\s+/g, '-')}-${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showNotification('Data exported successfully', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showNotification('Failed to export data', 'danger');
    }
}

// Settings
function showSettings() {
    alert('Settings panel coming soon!\n\nPlanned features:\n- Auto-refresh interval\n- Notification preferences\n- Alert thresholds\n- Map display options\n- Dark mode');
}

// Toggle metrics section
function toggleMetrics() {
    const section = document.getElementById('metrics-section');
    section.classList.toggle('expanded');

    // Save preference to localStorage
    const isExpanded = section.classList.contains('expanded');
    localStorage.setItem('metricsExpanded', isExpanded);
}

// Update quick view metrics
function updateQuickMetrics(data) {
    // Risk score
    if (data.anomaly_analysis) {
        const riskScore = data.anomaly_analysis.anomaly_score;
        const riskLevel = data.anomaly_analysis.risk_level;
        document.getElementById('quick-risk').textContent = riskScore;
        document.getElementById('quick-risk').style.color =
            riskLevel === 'critical' ? 'var(--color-danger)' :
            riskLevel === 'high' ? 'var(--color-danger)' :
            riskLevel === 'medium' ? 'var(--color-warning)' :
            'var(--color-success)';
    }

    // Location
    if (data.location) {
        const lat = data.location.latitude.toFixed(2);
        const lng = data.location.longitude.toFixed(2);
        document.getElementById('quick-location').textContent = `${lat}°, ${lng}°`;
        document.getElementById('quick-location').style.color = 'var(--color-success)';
    }

    // Device
    if (data.device_status) {
        const network = data.device_status.network_type || '—';
        document.getElementById('quick-device').textContent = network;
        document.getElementById('quick-device').style.color = 'var(--color-success)';
    }

    // Battery
    if (data.device_status && data.device_status.battery_level) {
        const battery = data.device_status.battery_level;
        document.getElementById('quick-battery').textContent = battery + '%';
        document.getElementById('quick-battery').style.color =
            battery < 20 ? 'var(--color-danger)' :
            battery < 50 ? 'var(--color-warning)' :
            'var(--color-success)';
    }
}

// Delete patient
async function deletePatient(patientId) {
    const patient = patients.find(p => p.id === patientId);
    if (!patient) return;

    // Confirm deletion
    const confirmDelete = confirm(`Are you sure you want to delete patient "${patient.full_name}"?\n\nThis action cannot be undone.`);
    if (!confirmDelete) return;

    try {
        const response = await fetch(`${API_BASE}/patients/${patientId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            console.log('✅ Patient deleted:', patientId);

            // If deleted patient was selected, clear dashboard
            if (currentPatientId === patientId) {
                currentPatientId = null;
                if (websocket) websocket.close();
                if (autoRefreshInterval) clearInterval(autoRefreshInterval);
                document.getElementById('dashboard-content').style.display = 'none';
                document.getElementById('no-patient-state').style.display = 'flex';
                document.getElementById('update-btn').style.display = 'none';
                document.getElementById('header-status-badge').style.display = 'none';
            }

            // Reload patient list
            await loadPatients();

            showNotification(`Patient "${patient.full_name}" deleted successfully`, 'success');
        } else {
            throw new Error('Failed to delete patient');
        }
    } catch (error) {
        console.error('Delete patient error:', error);
        showNotification('Failed to delete patient', 'danger');
    }
}

// Toggle sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.getElementById('hamburger-btn');

    sidebar.classList.toggle('collapsed');
    hamburger.classList.toggle('active');
    document.body.classList.toggle('sidebar-collapsed');

    // Save preference to localStorage
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebarCollapsed', isCollapsed);
}

// Initialize
window.addEventListener('load', () => {
    loadPatients();
    updateConnectionStatus(false, 'connecting');

    // Restore metrics expanded state
    const metricsExpanded = localStorage.getItem('metricsExpanded');
    if (metricsExpanded === 'true') {
        document.getElementById('metrics-section').classList.add('expanded');
    }

    // Restore sidebar collapsed state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed');
    if (sidebarCollapsed === 'true') {
        document.getElementById('sidebar').classList.add('collapsed');
        document.getElementById('hamburger-btn').classList.add('active');
        document.body.classList.add('sidebar-collapsed');
    }
});

window.addEventListener('beforeunload', () => {
    if (websocket) websocket.close();
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
});


// ============================================================================
// AI AGENT (MCP DEMO) Functions
// ============================================================================

function showAIAgentModal() {
    document.getElementById('ai-agent-modal').style.display = 'flex';
}

function hideAIAgentModal() {
    document.getElementById('ai-agent-modal').style.display = 'none';
}

function toggleAIInsights() {
    const contentWrapper = document.getElementById('ai-insights-content-wrapper');
    const toggle = document.getElementById('ai-insights-toggle');

    if (contentWrapper.style.maxHeight === '0px' || contentWrapper.style.maxHeight === '') {
        contentWrapper.style.maxHeight = '400px';
        toggle.style.transform = 'rotate(0deg)';
        toggle.textContent = '▼';
    } else {
        contentWrapper.style.maxHeight = '0px';
        toggle.style.transform = 'rotate(-90deg)';
        toggle.textContent = '▶';
    }
}

function clearAgentResults() {
    document.getElementById('agent-results').style.display = 'none';
    document.getElementById('tool-calls-timeline').innerHTML = '';
    document.getElementById('agent-final-response').style.display = 'none';
    document.getElementById('agent-summary').style.display = 'none';
}

async function runAIAgent() {
    const query = document.getElementById('agent-query').value.trim();

    if (!query) {
        showNotification('Please enter a query for the AI agent', 'warning');
        return;
    }

    // Show results area
    document.getElementById('agent-results').style.display = 'block';
    document.getElementById('agent-status').style.display = 'block';
    document.getElementById('tool-calls-timeline').innerHTML = '';
    document.getElementById('agent-final-response').style.display = 'none';
    document.getElementById('agent-summary').style.display = 'none';

    // Disable button
    const btn = document.getElementById('run-agent-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="loading-spinner" style="width: 16px; height: 16px;"></div><span>Running...</span>';

    try {
        const response = await fetch(`${API_BASE}/agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                max_iterations: 8
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Agent failed');
        }

        // Hide status
        document.getElementById('agent-status').style.display = 'none';

        // Display tool calls timeline
        displayToolCallsTimeline(data.actions_taken || []);

        // Display final response
        displayAgentFinalResponse(data.final_response || 'No response generated', data.success);

        // Display summary
        displayAgentSummary(data);

    } catch (error) {
        console.error('AI Agent error:', error);
        document.getElementById('agent-status').innerHTML = `
            <div style="display: flex; align-items: start; gap: 0.75rem; color: #DC2626;">
                <span style="font-size: 1.5rem;">❌</span>
                <div>
                    <div style="font-weight: 600;">Agent Error</div>
                    <div style="font-size: 0.875rem; margin-top: 0.25rem;">${error.message}</div>
                </div>
            </div>
        `;
        showNotification('AI Agent failed: ' + error.message, 'danger');
    } finally {
        // Re-enable button
        btn.disabled = false;
        btn.innerHTML = '<span>🚀</span><span>Run AI Agent</span>';
    }
}

function displayToolCallsTimeline(actions) {
    const timeline = document.getElementById('tool-calls-timeline');

    if (actions.length === 0) {
        timeline.innerHTML = `
            <div style="padding: 1rem; background: #FEF3C7; border-radius: 8px; border-left: 4px solid #F59E0B; color: #92400E;">
                <strong>⚠️ No tools called</strong> - The agent completed without calling any tools.
            </div>
        `;
        return;
    }

    const toolIcons = {
        'get_patient_location': '📍',
        'check_device_status': '📱',
        'check_sim_swap': '🔄',
        'trigger_emergency_qos': '🚀',
        'create_safe_zone': '🗺️',
        'analyze_patient_safety': '🧠'
    };

    timeline.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 1rem; color: #374151; display: flex; align-items: center; gap: 0.5rem;">
            <span>🛠️</span>
            <span>Tool Execution Timeline</span>
        </div>
    `;

    actions.forEach((action, index) => {
        const icon = toolIcons[action.tool] || '🔧';
        const success = action.result?.success !== false;
        const message = action.result?.message || 'Completed';

        const toolCard = document.createElement('div');
        toolCard.style.cssText = `
            padding: 1rem;
            background: ${success ? '#F0FDF4' : '#FEF2F2'};
            border-left: 4px solid ${success ? '#10B981' : '#EF4444'};
            border-radius: 8px;
            margin-bottom: 0.75rem;
        `;

        toolCard.innerHTML = `
            <div style="display: flex; align-items: start; gap: 0.75rem;">
                <div style="font-size: 1.5rem;">${icon}</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">
                        Step ${index + 1}: ${action.tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div style="font-size: 0.875rem; color: #6B7280; font-family: 'Courier New', monospace; margin-bottom: 0.5rem;">
                        ${JSON.stringify(action.arguments, null, 2).substring(0, 100)}${JSON.stringify(action.arguments).length > 100 ? '...' : ''}
                    </div>
                    <div style="font-size: 0.875rem; color: ${success ? '#10B981' : '#EF4444'}; font-weight: 500;">
                        ${success ? '✅' : '❌'} ${message}
                    </div>
                </div>
            </div>
        `;

        timeline.appendChild(toolCard);
    });
}

function displayAgentFinalResponse(response, success) {
    const container = document.getElementById('agent-final-response');
    container.style.display = 'block';

    container.innerHTML = `
        <div style="margin-bottom: 1.5rem; padding: 1.5rem; background: ${success ? 'linear-gradient(135deg, #f6f9ff 0%, #ffffff 100%)' : '#FEF2F2'}; border-radius: 8px; border-left: 4px solid ${success ? '#4285F4' : '#EF4444'};">
            <div style="font-weight: 600; color: #1f2937; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; font-size: 1.125rem;">
                <span>${success ? '🤖' : '❌'}</span>
                <span>Gemini AI Analysis</span>
            </div>
            <div style="color: #374151; line-height: 1.7; white-space: pre-wrap;">
                ${response}
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #E5E7EB; font-size: 0.8125rem; color: #6B7280; display: flex; align-items: center; gap: 0.5rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="opacity: 0.7;">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V7.89l7-3.11v8.21z"/>
                </svg>
                Generated by Google Gemini 2.5 Flash • Model Context Protocol (MCP)
            </div>
        </div>
    `;
}

function displayAgentSummary(data) {
    const container = document.getElementById('agent-summary');
    container.style.display = 'block';

    document.getElementById('summary-tools').textContent = (data.actions_taken || []).length;
    document.getElementById('summary-iterations').textContent = data.iterations || 0;
    document.getElementById('summary-status').textContent = data.success ? '✅ Success' : '❌ Failed';
    document.getElementById('summary-status').style.color = data.success ? '#10B981' : '#EF4444';
}
