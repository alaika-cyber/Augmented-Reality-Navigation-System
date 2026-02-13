/**
 * Text-to-Speech Module – Client-side voice guidance using Web Speech API.
 * Falls back gracefully if not supported.
 */

class VoiceGuidance {
    constructor() {
        this.enabled = true;
        this.synth = window.speechSynthesis || null;
        this.rate = 1.0;
        this.pitch = 1.0;
        this.volume = 1.0;
        this.voice = null;
        this.lastMessage = '';
        this.lastSpeakTime = 0;
        this.cooldownMs = 2000; // Minimum time between same messages
        this.isReady = false;
        this._queue = [];
        this._speaking = false;
    }

    /**
     * Initialize TTS engine.
     */
    init() {
        if (!this.synth) {
            console.warn('[TTS] Speech synthesis not supported');
            this.isReady = false;
            return false;
        }

        // Load voices
        const loadVoices = () => {
            const voices = this.synth.getVoices();
            if (voices.length > 0) {
                // Prefer English voices
                this.voice = voices.find(v =>
                    v.lang.startsWith('en') && v.localService
                ) || voices.find(v =>
                    v.lang.startsWith('en')
                ) || voices[0];

                console.log('[TTS] Voice selected:', this.voice.name);
                this.isReady = true;
            }
        };

        loadVoices();

        // Some browsers load voices asynchronously
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = loadVoices;
        }

        // Mark as ready even if voices haven't loaded yet
        this.isReady = true;
        return true;
    }

    /**
     * Speak a message with cooldown protection.
     */
    speak(message, force = false) {
        if (!this.enabled || !this.synth || !message) return false;

        const now = Date.now();

        // Skip if same message within cooldown
        if (!force && message === this.lastMessage &&
            (now - this.lastSpeakTime) < this.cooldownMs) {
            return false;
        }

        this.lastMessage = message;
        this.lastSpeakTime = now;

        // Cancel current speech for urgent messages
        if (this.synth.speaking) {
            this.synth.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(message);
        utterance.rate = this.rate;
        utterance.pitch = this.pitch;
        utterance.volume = this.volume;
        if (this.voice) {
            utterance.voice = this.voice;
        }

        utterance.onend = () => {
            this._speaking = false;
        };

        utterance.onerror = (e) => {
            console.error('[TTS] Error:', e);
            this._speaking = false;
        };

        this._speaking = true;
        this.synth.speak(utterance);
        return true;
    }

    /**
     * Speak with priority - cancels current speech.
     */
    speakUrgent(message) {
        if (this.synth && this.synth.speaking) {
            this.synth.cancel();
        }
        return this.speak(message, true);
    }

    /**
     * Toggle voice on/off.
     */
    toggle() {
        this.enabled = !this.enabled;
        if (!this.enabled && this.synth) {
            this.synth.cancel();
        }
        return this.enabled;
    }

    /**
     * Set speech rate.
     */
    setRate(rate) {
        this.rate = Math.max(0.5, Math.min(2.0, rate));
    }

    /**
     * Stop all speech.
     */
    stop() {
        if (this.synth) {
            this.synth.cancel();
        }
        this._speaking = false;
    }
}

// Export singleton
const voiceGuidance = new VoiceGuidance();
