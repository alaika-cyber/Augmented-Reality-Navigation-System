/**
 * Camera Module – Handles camera access, frame capture, and stream management.
 */

class CameraManager {
    constructor() {
        this.stream = null;
        this.videoElement = null;
        this.captureCanvas = null;
        this.captureCtx = null;
        this.isActive = false;
        this.facingMode = 'environment'; // Rear camera
        this.captureWidth = 640;
        this.captureHeight = 480;
        this.captureQuality = 0.7; // JPEG quality
    }

    /**
     * Initialize camera with the given video element.
     */
    async init(videoElement, captureCanvas) {
        this.videoElement = videoElement;
        this.captureCanvas = captureCanvas;
        this.captureCtx = captureCanvas.getContext('2d');
    }

    /**
     * Start the camera stream.
     */
    async start() {
        try {
            const constraints = {
                video: {
                    facingMode: this.facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 },
                },
                audio: false,
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;

            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });

            // Set capture canvas size
            this.captureCanvas.width = this.captureWidth;
            this.captureCanvas.height = this.captureHeight;
            this.isActive = true;

            console.log('[Camera] Started:', this.stream.getVideoTracks()[0].label);
            return true;
        } catch (err) {
            console.error('[Camera] Failed to start:', err);
            this.isActive = false;
            return false;
        }
    }

    /**
     * Capture current frame as JPEG Blob.
     */
    captureFrame() {
        if (!this.isActive || !this.videoElement.videoWidth) return null;

        this.captureCtx.drawImage(
            this.videoElement,
            0, 0,
            this.captureWidth,
            this.captureHeight
        );

        return new Promise((resolve) => {
            this.captureCanvas.toBlob(
                (blob) => resolve(blob),
                'image/jpeg',
                this.captureQuality
            );
        });
    }

    /**
     * Capture frame as base64 string.
     */
    captureFrameBase64() {
        if (!this.isActive || !this.videoElement.videoWidth) return null;

        this.captureCtx.drawImage(
            this.videoElement,
            0, 0,
            this.captureWidth,
            this.captureHeight
        );

        return this.captureCanvas.toDataURL('image/jpeg', this.captureQuality);
    }

    /**
     * Stop camera stream.
     */
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        this.isActive = false;
        console.log('[Camera] Stopped');
    }

    /**
     * Switch between front and back camera.
     */
    async switchCamera() {
        this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
        this.stop();
        return this.start();
    }
}

// Export singleton
const camera = new CameraManager();
