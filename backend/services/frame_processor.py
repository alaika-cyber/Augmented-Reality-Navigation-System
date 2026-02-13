"""
Frame processing pipeline.

Orchestrates detection → decision → response for each camera frame.
Runs as an async-compatible pipeline for WebSocket integration.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Optional

import cv2
import numpy as np

from backend.models.schemas import FrameAnalysis, GPSCoordinates
from backend.services.decision_engine import DecisionEngine
from backend.services.detection import DetectionService
from backend.services.gps_service import GPSService
from backend.services.tts_service import TTSService

logger = logging.getLogger(__name__)


class FrameProcessor:
    """
    Central processing pipeline.
    Coordinates detection, decision-making, TTS, and GPS.
    """

    def __init__(self) -> None:
        self.detector = DetectionService()
        self.decision_engine = DecisionEngine()
        self.tts = TTSService()
        self.gps = GPSService()

        self._frame_id: int = 0
        self._fps: float = 0.0
        self._last_time: float = time.time()
        self._fps_alpha: float = 0.1  # Exponential moving average

    def initialize(self) -> None:
        """Load models and initialize services."""
        logger.info("Initializing frame processor...")
        self.detector.load_model()
        self.tts.initialize()
        logger.info("Frame processor ready.")

    def process_frame_bytes(self, frame_data: bytes) -> Optional[FrameAnalysis]:
        """
        Process a raw frame (JPEG/PNG bytes) from the WebSocket.
        Returns a FrameAnalysis or None on error.
        """
        try:
            # Decode image bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning("Failed to decode frame")
                return None

            return self._process(frame)
        except Exception as e:
            logger.error("Frame processing error: %s", e)
            return None

    def process_base64_frame(self, b64_data: str) -> Optional[FrameAnalysis]:
        """
        Process a base64-encoded frame.
        Handles data URI prefix (e.g., "data:image/jpeg;base64,...").
        """
        try:
            # Strip data URI prefix if present
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]

            frame_bytes = base64.b64decode(b64_data)
            return self.process_frame_bytes(frame_bytes)
        except Exception as e:
            logger.error("Base64 frame error: %s", e)
            return None

    def _process(self, frame: np.ndarray) -> FrameAnalysis:
        """Core processing pipeline."""
        self._frame_id += 1
        now = time.time()

        # Calculate FPS (exponential moving average)
        dt = now - self._last_time
        if dt > 0:
            instant_fps = 1.0 / dt
            self._fps = self._fps_alpha * instant_fps + (1 - self._fps_alpha) * self._fps
        self._last_time = now

        # Step 1: Detect objects
        detections = self.detector.detect(frame)

        # Step 2: Make navigation decision
        analysis = self.decision_engine.analyze_frame(
            detections=detections,
            frame_id=self._frame_id,
            timestamp=now,
            fps=round(self._fps, 1),
        )

        # Step 3: Trigger TTS if needed
        if analysis.command.speak:
            self.tts.speak(analysis.command.message)

        return analysis

    def update_gps(self, coords: GPSCoordinates) -> None:
        """Update GPS coordinates from frontend."""
        self.gps.update_coordinates(coords)

    def get_status(self) -> dict:
        """Get system status."""
        return {
            "detection_ready": self.detector.is_ready,
            "tts_ready": self.tts.is_ready,
            "gps_active": self.gps.is_active,
            "camera_active": self._frame_id > 0,
            "fps": round(self._fps, 1),
            "model_loaded": self.detector.model_name,
            "device": self.detector.device,
            "frames_processed": self._frame_id,
        }

    def shutdown(self) -> None:
        """Clean up resources."""
        self.tts.shutdown()
        self.gps.deactivate()
        logger.info("Frame processor shut down.")
