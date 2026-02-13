"""
Application configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class DetectionConfig:
    """YOLOv8 detection configuration."""
    model_path: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    confidence_threshold: float = float(os.getenv("YOLO_CONFIDENCE", "0.45"))
    iou_threshold: float = float(os.getenv("YOLO_IOU", "0.5"))
    device: str = os.getenv("YOLO_DEVICE", "cpu")  # "cpu", "cuda", "mps"
    frame_skip: int = int(os.getenv("FRAME_SKIP", "2"))  # Process every Nth frame
    input_size: int = int(os.getenv("YOLO_INPUT_SIZE", "640"))

    # Custom model for stairs/pothole/wall detection
    custom_model_path: str = os.getenv("CUSTOM_MODEL_PATH", "")

    # COCO class IDs we care about
    # person=0, bicycle=1, car=2, motorcycle=3, bus=5, truck=7
    vehicle_class_ids: List[int] = field(default_factory=lambda: [1, 2, 3, 5, 7])
    person_class_id: int = 0

    # Detection zone ratios (0.0 to 1.0 of frame width)
    left_zone_end: float = 0.33
    center_zone_end: float = 0.66


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    engine: str = os.getenv("TTS_ENGINE", "pyttsx3")  # "pyttsx3" or "gtts"
    rate: int = int(os.getenv("TTS_RATE", "175"))
    volume: float = float(os.getenv("TTS_VOLUME", "1.0"))
    voice_id: str = os.getenv("TTS_VOICE", "")
    cooldown_seconds: float = float(os.getenv("TTS_COOLDOWN", "2.0"))


@dataclass
class GPSConfig:
    """GPS module configuration."""
    update_interval: float = float(os.getenv("GPS_INTERVAL", "5.0"))
    emergency_message: str = os.getenv(
        "EMERGENCY_MSG",
        "Emergency! I need help. My current location:"
    )


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    port: int = int(os.getenv("SERVER_PORT", "8000"))
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    ws_max_size: int = int(os.getenv("WS_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@dataclass
class AppConfig:
    """Root application configuration."""
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    gps: GPSConfig = field(default_factory=GPSConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


# Singleton config instance
config = AppConfig()
