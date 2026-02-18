"""
Pydantic models for request/response schemas and internal data structures.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ObjectCategory(str, Enum):
    PERSON = "person"
    VEHICLE = "vehicle"
    STAIRS = "stairs"
    WALL = "wall"
    POTHOLE = "pothole"
    OBSTACLE = "obstacle"
    ANIMAL = "animal"
    GLASS = "glass"
    UTENSIL = "utensil"
    FURNITURE = "furniture"
    DOOR = "door"
    WINDOW = "window"
    ELECTRONICS = "electronics"
    APPLIANCE = "appliance"
    FOOD = "food"
    PERSONAL_ITEM = "personal_item"
    SPORTS = "sports"
    TRAFFIC_SIGN = "traffic_sign"
    PLANT = "plant"
    WATER = "water"
    UNKNOWN = "unknown"


class Zone(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class NavigationAction(str, Enum):
    GO_STRAIGHT = "go_straight"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    STOP = "stop"
    CAUTION = "caution"


class DetectionResult(BaseModel):
    """Single detected object."""
    category: ObjectCategory
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: List[float] = Field(description="[x1, y1, x2, y2] normalized 0-1")
    zone: Zone
    label: str = ""


class NavigationCommand(BaseModel):
    """Navigation instruction produced by the decision engine."""
    action: NavigationAction
    message: str
    priority: int = Field(default=0, ge=0, le=10, description="Higher = more urgent")
    speak: bool = True


class FrameAnalysis(BaseModel):
    """Full analysis result for a single camera frame."""
    frame_id: int = 0
    timestamp: float = 0.0
    detections: List[DetectionResult] = []
    command: NavigationCommand = NavigationCommand(
        action=NavigationAction.GO_STRAIGHT,
        message="Path is clear. Go straight.",
        priority=0,
    )
    fps: float = 0.0


class GPSCoordinates(BaseModel):
    """GPS position."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: float = 0.0


class EmergencyAlert(BaseModel):
    """Emergency alert with location."""
    message: str
    coordinates: GPSCoordinates
    maps_link: str
    timestamp: float = 0.0


class SystemStatus(BaseModel):
    """System health status."""
    detection_ready: bool = False
    tts_ready: bool = False
    gps_active: bool = False
    camera_active: bool = False
    fps: float = 0.0
    model_loaded: str = ""
    device: str = "cpu"


class WebSocketMessage(BaseModel):
    """WebSocket communication envelope."""
    type: str  # "frame", "gps", "emergency", "status", "command"
    data: dict = {}
