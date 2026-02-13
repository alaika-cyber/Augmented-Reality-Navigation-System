/**
 * WebSocket Module – Manages real-time connection to the backend.
 */

class WSConnection {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.onAnalysis = null; // Callback for analysis results
        this.onStatus = null;
        this.onError = null;
        this.onEmergency = null;
        this.onConnect = null;
        this.onDisconnect = null;
    }

    /**
     * Connect to the WebSocket server.
     */
    connect(url) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

        try {
            this.ws = new WebSocket(url);
            this.ws.binaryType = 'arraybuffer';

            this.ws.onopen = () => {
                console.log('[WS] Connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                if (this.onConnect) this.onConnect();
            };

            this.ws.onmessage = (event) => {
                this._handleMessage(event);
            };

            this.ws.onclose = (event) => {
                console.log('[WS] Disconnected:', event.code);
                this.isConnected = false;
                if (this.onDisconnect) this.onDisconnect();
                this._tryReconnect(url);
            };

            this.ws.onerror = (error) => {
                console.error('[WS] Error:', error);
                if (this.onError) this.onError(error);
            };
        } catch (err) {
            console.error('[WS] Connection failed:', err);
            this._tryReconnect(url);
        }
    }

    /**
     * Send a binary frame (JPEG blob) to the server.
     */
    async sendFrame(blob) {
        if (!this.isConnected || !this.ws) return false;

        try {
            const buffer = await blob.arrayBuffer();
            this.ws.send(buffer);
            return true;
        } catch (err) {
            console.error('[WS] Send frame error:', err);
            return false;
        }
    }

    /**
     * Send a base64 frame via JSON.
     */
    sendFrameBase64(base64Data) {
        return this.sendJSON({
            type: 'frame',
            data: { image: base64Data }
        });
    }

    /**
     * Send GPS coordinates.
     */
    sendGPS(coords) {
        return this.sendJSON({
            type: 'gps',
            data: {
                latitude: coords.latitude,
                longitude: coords.longitude,
                accuracy: coords.accuracy || null,
                altitude: coords.altitude || null,
                speed: coords.speed || null,
                heading: coords.heading || null,
                timestamp: Date.now() / 1000
            }
        });
    }

    /**
     * Send emergency alert request.
     */
    sendEmergency() {
        return this.sendJSON({ type: 'emergency', data: {} });
    }

    /**
     * Request status update.
     */
    requestStatus() {
        return this.sendJSON({ type: 'status', data: {} });
    }

    /**
     * Send JSON message.
     */
    sendJSON(obj) {
        if (!this.isConnected || !this.ws) return false;
        try {
            this.ws.send(JSON.stringify(obj));
            return true;
        } catch (err) {
            console.error('[WS] Send JSON error:', err);
            return false;
        }
    }

    /**
     * Handle incoming messages.
     */
    _handleMessage(event) {
        try {
            const msg = JSON.parse(event.data);
            switch (msg.type) {
                case 'analysis':
                    if (this.onAnalysis) this.onAnalysis(msg.data);
                    break;
                case 'status':
                    if (this.onStatus) this.onStatus(msg.data);
                    break;
                case 'emergency':
                    if (this.onEmergency) this.onEmergency(msg.data);
                    break;
                case 'gps_ack':
                    console.log('[WS] GPS acknowledged');
                    break;
                case 'error':
                    console.error('[WS] Server error:', msg.data.message);
                    if (this.onError) this.onError(msg.data);
                    break;
                default:
                    console.log('[WS] Unknown message type:', msg.type);
            }
        } catch (err) {
            console.error('[WS] Parse error:', err);
        }
    }

    /**
     * Try to reconnect with exponential backoff.
     */
    _tryReconnect(url) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WS] Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => this.connect(url), delay);
    }

    /**
     * Disconnect.
     */
    disconnect() {
        if (this.ws) {
            this.ws.onclose = null; // Prevent reconnect
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }
}

// Export singleton
const wsConnection = new WSConnection();
