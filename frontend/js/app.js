/**
 * Main Application – Orchestrates all modules.
 *
 * Flow:
 *   1. App opens → camera ON, GPS ON, connect to backend
 *   2. Continuously capture frames → send to backend via WebSocket
 *   3. Receive analysis → render AR overlays + voice guidance
 *   4. Loop runs until app is closed
 */

class ARNavigationApp {
    constructor() {
        this.isRunning = false;
        this.frameInterval = null;
        this.frameRate = 10; // Frames per second to send
        this.voiceEnabled = true;
        this.showDetections = true;
        this.lastAnalysis = null;
        this.emergencyData = null;

        // Action icons mapping
        this.actionIcons = {
            go_straight: '⬆️',
            move_left: '⬅️',
            move_right: '➡️',
            stop: '🛑',
            caution: '⚠️',
        };
    }

    /**
     * Initialize all systems and prepare for launch.
     */
    async init() {
        console.log('[App] Initializing AR Navigation System...');

        // Initialize camera
        this._updateStep('step-camera', 'Initializing...');
        const videoEl = document.getElementById('camera-feed');
        const captureCanvas = document.getElementById('capture-canvas');
        await camera.init(videoEl, captureCanvas);
        const camOk = await camera.start();
        this._updateStep('step-camera', camOk ? '✓ Ready' : '✗ Failed', camOk);

        // Initialize GPS
        this._updateStep('step-gps', 'Initializing...');
        const gpsOk = gpsManager.isSupported();
        if (gpsOk) {
            gpsManager.onUpdate = (coords) => this._onGPSUpdate(coords);
            gpsManager.onError = (err) => console.warn('[GPS]', err.message);
            gpsManager.start();
        }
        this._updateStep('step-gps', gpsOk ? '✓ Ready' : '✗ N/A', gpsOk);

        // Initialize TTS
        this._updateStep('step-voice', 'Initializing...');
        const ttsOk = voiceGuidance.init();
        this._updateStep('step-voice', ttsOk ? '✓ Ready' : '✗ N/A', ttsOk);

        // Initialize AR Renderer
        const arCanvas = document.getElementById('ar-canvas');
        arRenderer.init(arCanvas);

        // Connect WebSocket
        this._updateStep('step-ai', 'Connecting...');
        this._setupWebSocket();

        // Show start button
        document.getElementById('start-btn').classList.remove('hidden');
        document.getElementById('loading-status').textContent = 'System ready. Tap Start.';

        // Listen to settings changes
        this._setupSettings();
    }

    /**
     * Start the main processing loop.
     */
    start() {
        if (this.isRunning) return;

        // Hide loading, show AR view
        document.getElementById('loading-screen').classList.add('hidden');
        document.getElementById('ar-view').classList.remove('hidden');

        // Resize AR canvas to video size
        const video = document.getElementById('camera-feed');
        const resizeCanvas = () => {
            arRenderer.resize(video.videoWidth || window.innerWidth, video.videoHeight || window.innerHeight);
        };
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Start frame capture loop
        this.isRunning = true;
        this._startFrameLoop();

        // Welcome message
        voiceGuidance.speak('Navigation started. Walk safely.');
        this._showToast('Navigation active', 'success');

        console.log('[App] Navigation started');
    }

    /**
     * Start sending frames to backend at configured rate.
     */
    _startFrameLoop() {
        const intervalMs = 1000 / this.frameRate;

        this.frameInterval = setInterval(async () => {
            if (!this.isRunning || !camera.isActive || !wsConnection.isConnected) return;

            try {
                const blob = await camera.captureFrame();
                if (blob) {
                    wsConnection.sendFrame(blob);
                }
            } catch (err) {
                console.error('[App] Frame capture error:', err);
            }
        }, intervalMs);
    }

    /**
     * Set up WebSocket connection and callbacks.
     */
    _setupWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws`;

        wsConnection.onConnect = () => {
            this._updateConnectionStatus(true);
            this._updateStep('step-ai', '✓ Connected', true);
            this._showToast('AI engine connected', 'success');
        };

        wsConnection.onDisconnect = () => {
            this._updateConnectionStatus(false);
            this._showToast('Connection lost. Reconnecting...', 'warning');
        };

        wsConnection.onAnalysis = (data) => {
            this._handleAnalysis(data);
        };

        wsConnection.onEmergency = (data) => {
            this._handleEmergency(data);
        };

        wsConnection.onStatus = (data) => {
            console.log('[App] Server status:', data);
        };

        wsConnection.onError = (error) => {
            console.error('[App] Server error:', error);
        };

        wsConnection.connect(wsUrl);
    }

    /**
     * Handle analysis result from backend.
     */
    _handleAnalysis(data) {
        this.lastAnalysis = data;

        // Update FPS display
        document.getElementById('fps-value').textContent = data.fps || '—';

        // Update navigation command
        const command = data.command;
        if (command) {
            this._updateNavCommand(command);

            // Speak the command via client-side TTS
            if (command.speak && this.voiceEnabled) {
                voiceGuidance.speak(command.message);
            }
        }

        // Draw AR overlays
        if (data.detections && this.showDetections) {
            arRenderer.draw(data.detections);
            this._updateDetectionPanel(data.detections);
        }
    }

    /**
     * Update the navigation command display.
     */
    _updateNavCommand(command) {
        const navCmd = document.getElementById('nav-command');
        const navIcon = document.getElementById('nav-icon');
        const navMsg = document.getElementById('nav-message');

        // Update icon and message
        navIcon.textContent = this.actionIcons[command.action] || '❓';
        navMsg.textContent = command.message;

        // Update styling based on action
        navCmd.className = 'nav-command action-' + command.action;
    }

    /**
     * Update the detection tags panel.
     */
    _updateDetectionPanel(detections) {
        const list = document.getElementById('detection-list');
        if (!detections || detections.length === 0) {
            list.innerHTML = '';
            return;
        }

        // Group by category
        const counts = {};
        for (const det of detections) {
            if (!counts[det.category]) counts[det.category] = 0;
            counts[det.category]++;
        }

        let html = '';
        for (const [cat, count] of Object.entries(counts)) {
            const icon = arRenderer.icons[cat] || '❓';
            html += `<span class="detection-tag ${cat}">${icon} ${cat}${count > 1 ? ' ×' + count : ''}</span>`;
        }
        list.innerHTML = html;
    }

    /**
     * Handle GPS position update.
     */
    _onGPSUpdate(coords) {
        // Send to backend
        wsConnection.sendGPS(coords);

        // Update UI
        const gpsValue = document.getElementById('gps-value');
        gpsValue.textContent = `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`;
    }

    /**
     * Update connection status indicator.
     */
    _updateConnectionStatus(connected) {
        const dot = document.getElementById('conn-dot');
        const value = document.getElementById('conn-value');

        if (connected) {
            dot.classList.add('connected');
            value.textContent = 'Live';
        } else {
            dot.classList.remove('connected');
            value.textContent = 'Offline';
        }
    }

    /**
     * Toggle voice guidance.
     */
    toggleVoice() {
        this.voiceEnabled = voiceGuidance.toggle();
        const icon = document.getElementById('voice-icon');
        icon.textContent = this.voiceEnabled ? '🔊' : '🔇';
        this._showToast(this.voiceEnabled ? 'Voice ON' : 'Voice OFF', 'info');
    }

    /**
     * Trigger emergency alert.
     */
    async triggerEmergency() {
        // Vibrate if supported
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);

        voiceGuidance.speakUrgent('Emergency alert activated.');

        // Try to get fresh GPS position
        try {
            await gpsManager.getCurrentPosition();
        } catch (e) {
            console.warn('[Emergency] GPS unavailable');
        }

        // Send to backend
        wsConnection.sendEmergency();

        // Also generate client-side alert if we have GPS
        const emergencyText = gpsManager.getEmergencyText();
        const mapsLink = gpsManager.getMapsLink();

        document.getElementById('emergency-text').textContent = emergencyText;
        const linkEl = document.getElementById('emergency-maps-link');
        if (mapsLink) {
            linkEl.href = mapsLink;
            linkEl.classList.remove('hidden');
        } else {
            linkEl.classList.add('hidden');
        }

        this.emergencyData = { text: emergencyText, link: mapsLink };
        document.getElementById('emergency-modal').classList.remove('hidden');
    }

    /**
     * Handle emergency response from backend.
     */
    _handleEmergency(data) {
        if (data.maps_link) {
            const linkEl = document.getElementById('emergency-maps-link');
            linkEl.href = data.maps_link;
        }
        if (data.message) {
            document.getElementById('emergency-text').textContent = data.message;
        }
    }

    /**
     * Copy emergency text to clipboard.
     */
    async copyEmergencyText() {
        if (!this.emergencyData) return;
        try {
            await navigator.clipboard.writeText(this.emergencyData.text);
            this._showToast('Copied to clipboard', 'success');
        } catch (e) {
            // Fallback
            const ta = document.createElement('textarea');
            ta.value = this.emergencyData.text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            ta.remove();
            this._showToast('Copied', 'success');
        }
    }

    /**
     * Close emergency modal.
     */
    closeEmergency() {
        document.getElementById('emergency-modal').classList.add('hidden');
    }

    /**
     * Share current location.
     */
    async shareLocation() {
        const text = gpsManager.getEmergencyText();
        const link = gpsManager.getMapsLink();

        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'My Location',
                    text: text,
                    url: link,
                });
            } catch (e) {
                console.log('[Share] Cancelled or failed');
            }
        } else {
            // Copy to clipboard
            try {
                await navigator.clipboard.writeText(text);
                this._showToast('Location copied!', 'success');
            } catch (e) {
                this._showToast('Location unavailable', 'error');
            }
        }
    }

    /**
     * Toggle settings modal.
     */
    toggleSettings() {
        const modal = document.getElementById('settings-modal');
        modal.classList.toggle('hidden');
    }

    /**
     * Set up settings change listeners.
     */
    _setupSettings() {
        document.getElementById('setting-voice')?.addEventListener('change', (e) => {
            this.voiceEnabled = e.target.checked;
            voiceGuidance.enabled = e.target.checked;
        });

        document.getElementById('setting-detections')?.addEventListener('change', (e) => {
            this.showDetections = e.target.checked;
            arRenderer.enabled = e.target.checked;
            if (!e.target.checked) arRenderer.clear();
        });

        document.getElementById('setting-voice-speed')?.addEventListener('input', (e) => {
            voiceGuidance.setRate(parseFloat(e.target.value));
        });
    }

    /**
     * Update loading step status.
     */
    _updateStep(stepId, statusText, success = null) {
        const step = document.getElementById(stepId);
        if (!step) return;
        const statusEl = step.querySelector('.step-status');
        if (statusEl) statusEl.textContent = statusText;
        if (success === true) step.classList.add('ready');
        else if (success === false) step.classList.add('error');
    }

    /**
     * Show a toast notification.
     */
    _showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * Stop the application.
     */
    stop() {
        this.isRunning = false;
        if (this.frameInterval) {
            clearInterval(this.frameInterval);
            this.frameInterval = null;
        }
        camera.stop();
        gpsManager.stop();
        voiceGuidance.stop();
        wsConnection.disconnect();
        arRenderer.clear();
        console.log('[App] Navigation stopped');
    }
}

// ─── Bootstrap ──────────────────────────────────────────────────────
const app = new ARNavigationApp();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app.init().catch(err => {
        console.error('[App] Init failed:', err);
        document.getElementById('loading-status').textContent =
            'Initialization failed. Please reload.';
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    app.stop();
});
