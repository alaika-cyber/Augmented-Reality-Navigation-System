/**
 * GPS Module – Handles browser Geolocation API for position tracking.
 */

class GPSManager {
    constructor() {
        this.watchId = null;
        this.isActive = false;
        this.lastPosition = null;
        this.onUpdate = null;  // Callback for position updates
        this.onError = null;

        this.options = {
            enableHighAccuracy: true,
            maximumAge: 5000,
            timeout: 10000,
        };
    }

    /**
     * Check if geolocation is supported.
     */
    isSupported() {
        return 'geolocation' in navigator;
    }

    /**
     * Start watching position.
     */
    start() {
        if (!this.isSupported()) {
            console.warn('[GPS] Geolocation not supported');
            return false;
        }

        try {
            this.watchId = navigator.geolocation.watchPosition(
                (position) => this._onPosition(position),
                (error) => this._onError(error),
                this.options
            );
            this.isActive = true;
            console.log('[GPS] Watching started');
            return true;
        } catch (err) {
            console.error('[GPS] Start error:', err);
            return false;
        }
    }

    /**
     * Get current position (one-shot).
     */
    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!this.isSupported()) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this._onPosition(position);
                    resolve(this.lastPosition);
                },
                (error) => {
                    reject(error);
                },
                this.options
            );
        });
    }

    /**
     * Handle position update.
     */
    _onPosition(position) {
        this.lastPosition = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            speed: position.coords.speed,
            heading: position.coords.heading,
            timestamp: position.timestamp / 1000,
        };

        if (this.onUpdate) {
            this.onUpdate(this.lastPosition);
        }
    }

    /**
     * Handle GPS error.
     */
    _onError(error) {
        console.error('[GPS] Error:', error.message);
        if (this.onError) {
            this.onError(error);
        }
    }

    /**
     * Generate Google Maps link.
     */
    getMapsLink() {
        if (!this.lastPosition) return null;
        const { latitude, longitude } = this.lastPosition;
        return `https://www.google.com/maps?q=${latitude},${longitude}`;
    }

    /**
     * Generate emergency message with location.
     */
    getEmergencyText() {
        if (!this.lastPosition) return 'Location unavailable.';
        const link = this.getMapsLink();
        const { latitude, longitude, accuracy } = this.lastPosition;
        return `Emergency! I need help. My current location:\n${link}\nCoordinates: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}\nAccuracy: ${accuracy ? accuracy.toFixed(0) + 'm' : 'unknown'}`;
    }

    /**
     * Stop watching position.
     */
    stop() {
        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        this.isActive = false;
        console.log('[GPS] Stopped');
    }
}

// Export singleton
const gpsManager = new GPSManager();
