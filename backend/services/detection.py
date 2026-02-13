"""
YOLOv8 Object Detection Service.

Handles model loading, frame inference, and result parsing.
Detects: person, vehicle, stairs, wall, pothole, and generic obstacles.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from backend.config import config
from backend.models.schemas import DetectionResult, ObjectCategory, Zone

logger = logging.getLogger(__name__)


# Mapping from COCO class names to our categories
COCO_TO_CATEGORY = {
    "person": ObjectCategory.PERSON,
    "bicycle": ObjectCategory.VEHICLE,
    "car": ObjectCategory.VEHICLE,
    "motorcycle": ObjectCategory.VEHICLE,
    "bus": ObjectCategory.VEHICLE,
    "truck": ObjectCategory.VEHICLE,
    "train": ObjectCategory.VEHICLE,
    "bench": ObjectCategory.OBSTACLE,
    "chair": ObjectCategory.OBSTACLE,
    "couch": ObjectCategory.OBSTACLE,
    "dining table": ObjectCategory.OBSTACLE,
    "suitcase": ObjectCategory.OBSTACLE,
    "backpack": ObjectCategory.OBSTACLE,
    "fire hydrant": ObjectCategory.OBSTACLE,
    "stop sign": ObjectCategory.OBSTACLE,
    "parking meter": ObjectCategory.OBSTACLE,
}

# Custom model class mapping (if using a custom-trained model)
CUSTOM_CATEGORY_MAP = {
    "stairs": ObjectCategory.STAIRS,
    "staircase": ObjectCategory.STAIRS,
    "wall": ObjectCategory.WALL,
    "pothole": ObjectCategory.POTHOLE,
    "obstacle": ObjectCategory.OBSTACLE,
    "person": ObjectCategory.PERSON,
    "vehicle": ObjectCategory.VEHICLE,
    "car": ObjectCategory.VEHICLE,
    "bike": ObjectCategory.VEHICLE,
}


class DetectionService:
    """Real-time object detection using YOLOv8."""

    def __init__(self) -> None:
        self._model = None
        self._custom_model = None
        self._frame_count: int = 0
        self._last_results: List[DetectionResult] = []
        self._cfg = config.detection
        self._model_name: str = ""
        self._device: str = self._cfg.device

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    def load_model(self) -> None:
        """Load YOLOv8 model(s). Call once at startup."""
        try:
            from ultralytics import YOLO

            logger.info("Loading YOLOv8 model: %s", self._cfg.model_path)
            self._model = YOLO(self._cfg.model_path)

            # Warm-up inference
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(
                dummy,
                conf=self._cfg.confidence_threshold,
                device=self._device,
                verbose=False,
            )
            self._model_name = self._cfg.model_path
            logger.info("YOLOv8 model loaded on device=%s", self._device)

            # Load custom model if specified
            if self._cfg.custom_model_path:
                logger.info(
                    "Loading custom model: %s", self._cfg.custom_model_path
                )
                self._custom_model = YOLO(self._cfg.custom_model_path)
                self._custom_model.predict(
                    dummy,
                    conf=self._cfg.confidence_threshold,
                    device=self._device,
                    verbose=False,
                )
                logger.info("Custom model loaded.")

        except Exception as e:
            logger.error("Failed to load model: %s", e)
            raise

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Run detection on a frame.
        Uses frame skipping for performance – returns cached results on
        skipped frames.
        """
        self._frame_count += 1

        if self._frame_count % self._cfg.frame_skip != 0:
            return self._last_results

        if self._model is None:
            return []

        results: List[DetectionResult] = []
        h, w = frame.shape[:2]

        # --- Primary COCO model ---
        preds = self._model.predict(
            frame,
            conf=self._cfg.confidence_threshold,
            iou=self._cfg.iou_threshold,
            device=self._device,
            imgsz=self._cfg.input_size,
            verbose=False,
        )

        if preds and len(preds) > 0:
            for r in preds:
                boxes = r.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self._model.names.get(cls_id, "unknown")
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    category = COCO_TO_CATEGORY.get(cls_name, None)
                    if category is None:
                        continue

                    bbox_norm = [x1 / w, y1 / h, x2 / w, y2 / h]
                    zone = self._classify_zone(bbox_norm)

                    results.append(
                        DetectionResult(
                            category=category,
                            confidence=round(conf, 3),
                            bbox=bbox_norm,
                            zone=zone,
                            label=cls_name,
                        )
                    )

        # --- Custom model (stairs, wall, pothole) ---
        if self._custom_model is not None:
            custom_preds = self._custom_model.predict(
                frame,
                conf=self._cfg.confidence_threshold,
                iou=self._cfg.iou_threshold,
                device=self._device,
                imgsz=self._cfg.input_size,
                verbose=False,
            )
            if custom_preds and len(custom_preds) > 0:
                for r in custom_preds:
                    boxes = r.boxes
                    if boxes is None:
                        continue
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        cls_name = self._custom_model.names.get(cls_id, "unknown")
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        category = CUSTOM_CATEGORY_MAP.get(
                            cls_name.lower(), ObjectCategory.OBSTACLE
                        )
                        bbox_norm = [x1 / w, y1 / h, x2 / w, y2 / h]
                        zone = self._classify_zone(bbox_norm)

                        results.append(
                            DetectionResult(
                                category=category,
                                confidence=round(conf, 3),
                                bbox=bbox_norm,
                                zone=zone,
                                label=cls_name,
                            )
                        )

        # Apply simulated heuristic detections for stairs/wall/pothole
        # when no custom model is available
        if self._custom_model is None:
            heuristic = self._heuristic_detections(frame)
            results.extend(heuristic)

        self._last_results = results
        return results

    def _classify_zone(self, bbox: List[float]) -> Zone:
        """Determine which zone (left/center/right) a bounding box falls in."""
        cx = (bbox[0] + bbox[2]) / 2.0
        if cx < self._cfg.left_zone_end:
            return Zone.LEFT
        elif cx < self._cfg.center_zone_end:
            return Zone.CENTER
        else:
            return Zone.RIGHT

    def _heuristic_detections(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Simple heuristic/edge-based detection for stairs and walls
        when no custom YOLO model is available.
        Uses edge density analysis.
        """
        results: List[DetectionResult] = []
        h, w = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Analyze bottom third of frame for potential obstacles
        bottom_region = edges[int(h * 0.6):, :]
        bottom_h, bottom_w = bottom_region.shape

        # Check for strong horizontal lines (stairs indicator)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(bottom_region, cv2.MORPH_OPEN, horizontal_kernel)
        h_line_density = np.sum(horizontal_lines > 0) / (bottom_h * bottom_w + 1e-6)

        if h_line_density > 0.08:
            results.append(
                DetectionResult(
                    category=ObjectCategory.STAIRS,
                    confidence=min(0.6, h_line_density * 5),
                    bbox=[0.2, 0.6, 0.8, 1.0],
                    zone=Zone.CENTER,
                    label="stairs (heuristic)",
                )
            )

        # Check for vertical edges (wall indicator)
        left_strip = edges[:, :int(w * 0.15)]
        right_strip = edges[:, int(w * 0.85):]
        left_density = np.sum(left_strip > 0) / (left_strip.size + 1e-6)
        right_density = np.sum(right_strip > 0) / (right_strip.size + 1e-6)

        if left_density > 0.15:
            results.append(
                DetectionResult(
                    category=ObjectCategory.WALL,
                    confidence=min(0.55, left_density * 3),
                    bbox=[0.0, 0.0, 0.15, 1.0],
                    zone=Zone.LEFT,
                    label="wall (heuristic)",
                )
            )
        if right_density > 0.15:
            results.append(
                DetectionResult(
                    category=ObjectCategory.WALL,
                    confidence=min(0.55, right_density * 3),
                    bbox=[0.85, 0.0, 1.0, 1.0],
                    zone=Zone.RIGHT,
                    label="wall (heuristic)",
                )
            )

        return results
