/**
 * AR Renderer – Draws detection overlays on the AR canvas.
 */

class ARRenderer {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.enabled = true;

        // Colors for each category
        this.colors = {
            person:   { fill: 'rgba(41, 121, 255, 0.2)',  stroke: '#2979ff' },
            vehicle:  { fill: 'rgba(255, 23, 68, 0.2)',   stroke: '#ff1744' },
            stairs:   { fill: 'rgba(255, 171, 0, 0.2)',   stroke: '#ffab00' },
            wall:     { fill: 'rgba(158, 158, 158, 0.2)', stroke: '#9e9e9e' },
            pothole:  { fill: 'rgba(255, 109, 0, 0.2)',   stroke: '#ff6d00' },
            obstacle: { fill: 'rgba(224, 64, 251, 0.2)',  stroke: '#e040fb' },
            unknown:  { fill: 'rgba(255, 255, 255, 0.1)', stroke: '#ffffff' },
        };

        // Icons for categories
        this.icons = {
            person:   '🚶',
            vehicle:  '🚗',
            stairs:   '🪜',
            wall:     '🧱',
            pothole:  '⚠️',
            obstacle: '🚧',
            unknown:  '❓',
        };
    }

    /**
     * Initialize with canvas element.
     */
    init(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
    }

    /**
     * Resize canvas to match video dimensions.
     */
    resize(width, height) {
        if (this.canvas) {
            this.canvas.width = width;
            this.canvas.height = height;
        }
    }

    /**
     * Draw all detections on the canvas.
     */
    draw(detections) {
        if (!this.ctx || !this.enabled) return;

        const w = this.canvas.width;
        const h = this.canvas.height;

        // Clear previous drawings
        this.ctx.clearRect(0, 0, w, h);

        if (!detections || detections.length === 0) return;

        for (const det of detections) {
            this._drawDetection(det, w, h);
        }
    }

    /**
     * Draw a single detection bounding box with label.
     */
    _drawDetection(det, canvasW, canvasH) {
        const [nx1, ny1, nx2, ny2] = det.bbox;
        const x = nx1 * canvasW;
        const y = ny1 * canvasH;
        const bw = (nx2 - nx1) * canvasW;
        const bh = (ny2 - ny1) * canvasH;

        const color = this.colors[det.category] || this.colors.unknown;
        const icon = this.icons[det.category] || '❓';

        // Draw filled rectangle
        this.ctx.fillStyle = color.fill;
        this.ctx.fillRect(x, y, bw, bh);

        // Draw border
        this.ctx.strokeStyle = color.stroke;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, bw, bh);

        // Draw corner accents
        const cornerLen = Math.min(20, bw * 0.2, bh * 0.2);
        this.ctx.lineWidth = 3;
        this.ctx.strokeStyle = color.stroke;

        // Top-left
        this.ctx.beginPath();
        this.ctx.moveTo(x, y + cornerLen);
        this.ctx.lineTo(x, y);
        this.ctx.lineTo(x + cornerLen, y);
        this.ctx.stroke();

        // Top-right
        this.ctx.beginPath();
        this.ctx.moveTo(x + bw - cornerLen, y);
        this.ctx.lineTo(x + bw, y);
        this.ctx.lineTo(x + bw, y + cornerLen);
        this.ctx.stroke();

        // Bottom-left
        this.ctx.beginPath();
        this.ctx.moveTo(x, y + bh - cornerLen);
        this.ctx.lineTo(x, y + bh);
        this.ctx.lineTo(x + cornerLen, y + bh);
        this.ctx.stroke();

        // Bottom-right
        this.ctx.beginPath();
        this.ctx.moveTo(x + bw - cornerLen, y + bh);
        this.ctx.lineTo(x + bw, y + bh);
        this.ctx.lineTo(x + bw, y + bh - cornerLen);
        this.ctx.stroke();

        // Draw label background
        const label = `${icon} ${det.label || det.category} ${Math.round(det.confidence * 100)}%`;
        this.ctx.font = '12px -apple-system, sans-serif';
        const textMetrics = this.ctx.measureText(label);
        const labelH = 20;
        const labelW = textMetrics.width + 12;

        this.ctx.fillStyle = color.stroke;
        this.ctx.fillRect(x, y - labelH, labelW, labelH);

        // Draw label text
        this.ctx.fillStyle = '#ffffff';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(label, x + 6, y - labelH / 2);
    }

    /**
     * Draw zone indicators (left/center/right dividers).
     */
    drawZones() {
        if (!this.ctx) return;
        const w = this.canvas.width;
        const h = this.canvas.height;

        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([8, 8]);

        // Left zone line
        this.ctx.beginPath();
        this.ctx.moveTo(w * 0.33, 0);
        this.ctx.lineTo(w * 0.33, h);
        this.ctx.stroke();

        // Right zone line
        this.ctx.beginPath();
        this.ctx.moveTo(w * 0.66, 0);
        this.ctx.lineTo(w * 0.66, h);
        this.ctx.stroke();

        this.ctx.setLineDash([]);
    }

    /**
     * Clear the canvas.
     */
    clear() {
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    /**
     * Toggle overlay visibility.
     */
    toggle() {
        this.enabled = !this.enabled;
        if (!this.enabled) this.clear();
        return this.enabled;
    }
}

// Export singleton
const arRenderer = new ARRenderer();
