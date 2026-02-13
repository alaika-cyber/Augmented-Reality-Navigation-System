"""
Tests for the Decision Engine.
"""

import pytest

from backend.models.schemas import (
    DetectionResult,
    NavigationAction,
    ObjectCategory,
    Zone,
)
from backend.services.decision_engine import DecisionEngine


@pytest.fixture
def engine():
    return DecisionEngine()


def _det(category, zone, confidence=0.8, bbox=None):
    """Helper to create a DetectionResult."""
    zone_bbox = {
        Zone.LEFT: [0.05, 0.3, 0.25, 0.8],
        Zone.CENTER: [0.35, 0.3, 0.65, 0.8],
        Zone.RIGHT: [0.75, 0.3, 0.95, 0.8],
    }
    return DetectionResult(
        category=category,
        confidence=confidence,
        bbox=bbox or zone_bbox[zone],
        zone=zone,
        label=category.value,
    )


class TestDecisionEngine:
    def test_no_detections_go_straight(self, engine):
        cmd = engine.decide([])
        assert cmd.action == NavigationAction.GO_STRAIGHT
        assert "clear" in cmd.message.lower() or "straight" in cmd.message.lower()

    def test_obstacle_center_move_left(self, engine):
        detections = [_det(ObjectCategory.OBSTACLE, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.MOVE_LEFT

    def test_obstacle_center_left_blocked_move_right(self, engine):
        detections = [
            _det(ObjectCategory.OBSTACLE, Zone.CENTER),
            _det(ObjectCategory.WALL, Zone.LEFT),
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.MOVE_RIGHT

    def test_all_sides_blocked_stop(self, engine):
        detections = [
            _det(ObjectCategory.OBSTACLE, Zone.CENTER),
            _det(ObjectCategory.WALL, Zone.LEFT),
            _det(ObjectCategory.WALL, Zone.RIGHT),
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP

    def test_vehicle_close_stop(self, engine):
        # Large bounding box = close vehicle
        detections = [
            _det(ObjectCategory.VEHICLE, Zone.CENTER, bbox=[0.1, 0.1, 0.9, 0.9])
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP
        assert "vehicle" in cmd.message.lower()

    def test_vehicle_far_caution(self, engine):
        # Small bounding box = far vehicle
        detections = [
            _det(ObjectCategory.VEHICLE, Zone.CENTER, bbox=[0.4, 0.4, 0.6, 0.6])
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.CAUTION

    def test_stairs_detected(self, engine):
        detections = [_det(ObjectCategory.STAIRS, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.CAUTION
        assert "stairs" in cmd.message.lower()

    def test_pothole_center_move_left(self, engine):
        detections = [_det(ObjectCategory.POTHOLE, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.MOVE_LEFT
        assert "pothole" in cmd.message.lower()

    def test_person_to_side_go_straight(self, engine):
        detections = [_det(ObjectCategory.PERSON, Zone.RIGHT)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.GO_STRAIGHT

    def test_person_center_is_obstacle(self, engine):
        detections = [_det(ObjectCategory.PERSON, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.MOVE_LEFT

    def test_priority_vehicle_over_obstacle(self, engine):
        detections = [
            _det(ObjectCategory.OBSTACLE, Zone.CENTER),
            _det(ObjectCategory.VEHICLE, Zone.CENTER, bbox=[0.1, 0.1, 0.9, 0.9]),
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP
        assert "vehicle" in cmd.message.lower()

    def test_frame_analysis(self, engine):
        detections = [_det(ObjectCategory.STAIRS, Zone.CENTER)]
        analysis = engine.analyze_frame(detections, frame_id=42, fps=15.0)
        assert analysis.frame_id == 42
        assert analysis.fps == 15.0
        assert len(analysis.detections) == 1
        assert analysis.command.action == NavigationAction.CAUTION
