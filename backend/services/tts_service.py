"""
Text-to-Speech Service.

Provides offline TTS using pyttsx3 with a cooldown mechanism
to avoid spamming audio instructions.
Also supports Web Speech API fallback via sending text to frontend.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from backend.config import config

logger = logging.getLogger(__name__)


class TTSService:
    """Thread-safe text-to-speech with cooldown."""

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()
        self._last_speak_time: float = 0.0
        self._last_message: str = ""
        self._cfg = config.tts
        self._ready = False
        self._use_server_tts = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def initialize(self) -> None:
        """Initialize TTS engine. Gracefully falls back if unavailable."""
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._cfg.rate)
            self._engine.setProperty("volume", self._cfg.volume)

            # Set voice if specified
            if self._cfg.voice_id:
                self._engine.setProperty("voice", self._cfg.voice_id)

            self._ready = True
            self._use_server_tts = True
            logger.info("pyttsx3 TTS engine initialized (rate=%d)", self._cfg.rate)
        except Exception as e:
            logger.warning(
                "pyttsx3 not available (%s). TTS will be handled by frontend.",
                e,
            )
            self._ready = True
            self._use_server_tts = False

    def speak(self, text: str, force: bool = False) -> bool:
        """
        Speak the given text if cooldown has elapsed.
        Returns True if speech was triggered.
        """
        now = time.time()

        # Skip if same message and within cooldown
        if not force:
            if (
                text == self._last_message
                and now - self._last_speak_time < self._cfg.cooldown_seconds
            ):
                return False

        self._last_message = text
        self._last_speak_time = now

        if self._use_server_tts and self._engine is not None:
            # Run TTS in background thread to avoid blocking
            thread = threading.Thread(
                target=self._speak_sync, args=(text,), daemon=True
            )
            thread.start()
            return True

        # Frontend will handle TTS
        return True

    def _speak_sync(self, text: str) -> None:
        """Synchronous speech (runs in thread)."""
        with self._lock:
            try:
                if self._engine is not None:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception as e:
                logger.error("TTS speak error: %s", e)

    def should_speak(self, text: str) -> bool:
        """Check if cooldown allows speaking (without actually speaking)."""
        now = time.time()
        if (
            text == self._last_message
            and now - self._last_speak_time < self._cfg.cooldown_seconds
        ):
            return False
        return True

    def shutdown(self) -> None:
        """Clean up TTS engine."""
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._engine = None
                self._ready = False
