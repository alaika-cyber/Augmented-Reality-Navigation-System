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

    # ── New category tests ──

    def test_animal_large_center_stop(self, engine):
        """Large animal in center → stop."""
        detections = [
            DetectionResult(
                category=ObjectCategory.ANIMAL,
                confidence=0.85,
                bbox=[0.1, 0.1, 0.8, 0.8],
                zone=Zone.CENTER,
                label="horse",
            )
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP
        assert "animal" in cmd.message.lower() or "horse" in cmd.message.lower()

    def test_animal_small_center_caution(self, engine):
        """Small animal in center → caution."""
        detections = [
            DetectionResult(
                category=ObjectCategory.ANIMAL,
                confidence=0.75,
                bbox=[0.4, 0.5, 0.6, 0.7],
                zone=Zone.CENTER,
                label="cat",
            )
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.CAUTION
        assert "cat" in cmd.message.lower()

    def test_animal_side_caution(self, engine):
        """Animal to the side → informational caution."""
        detections = [_det(ObjectCategory.ANIMAL, Zone.LEFT)]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.CAUTION
        assert "left" in cmd.message.lower()

    def test_glass_center_caution(self, engine):
        """Glass object in center → caution."""
        detections = [
            DetectionResult(
                category=ObjectCategory.GLASS,
                confidence=0.7,
                bbox=[0.35, 0.3, 0.65, 0.8],
                zone=Zone.CENTER,
                label="wine glass",
            )
        ]
        cmd = engine.decide(detections)
        assert "glass" in cmd.message.lower()

    def test_water_center_move_left(self, engine):
        """Water hazard in center → move left."""
        detections = [
            DetectionResult(
                category=ObjectCategory.WATER,
                confidence=0.8,
                bbox=[0.35, 0.5, 0.65, 0.9],
                zone=Zone.CENTER,
                label="puddle",
            )
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.MOVE_LEFT
        assert "water" in cmd.message.lower() or "puddle" in cmd.message.lower()

    def test_water_center_all_blocked_stop(self, engine):
        """Water in center with both sides blocked → stop."""
        detections = [
            DetectionResult(
                category=ObjectCategory.WATER,
                confidence=0.8,
                bbox=[0.35, 0.5, 0.65, 0.9],
                zone=Zone.CENTER,
                label="water",
            ),
            _det(ObjectCategory.WALL, Zone.LEFT),
            _det(ObjectCategory.WALL, Zone.RIGHT),
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP

    def test_furniture_center_move(self, engine):
        """Furniture in center → navigate around it."""
        detections = [_det(ObjectCategory.FURNITURE, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action in (NavigationAction.MOVE_LEFT, NavigationAction.MOVE_RIGHT)

    def test_door_detected(self, engine):
        """Door detected → caution about opening."""
        detections = [_det(ObjectCategory.DOOR, Zone.CENTER)]
        cmd = engine.decide(detections)
        # Door is both a blocking obstacle and door-specific warning
        assert cmd.action in (NavigationAction.CAUTION, NavigationAction.MOVE_LEFT)

    def test_traffic_light_caution(self, engine):
        """Traffic light → caution."""
        detections = [
            DetectionResult(
                category=ObjectCategory.TRAFFIC_SIGN,
                confidence=0.9,
                bbox=[0.4, 0.1, 0.6, 0.4],
                zone=Zone.CENTER,
                label="traffic light",
            )
        ]
        cmd = engine.decide(detections)
        assert "traffic light" in cmd.message.lower()

    def test_stop_sign_stop(self, engine):
        """Stop sign → stop."""
        detections = [
            DetectionResult(
                category=ObjectCategory.TRAFFIC_SIGN,
                confidence=0.9,
                bbox=[0.4, 0.1, 0.6, 0.4],
                zone=Zone.CENTER,
                label="stop sign",
            )
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP

    def test_utensil_knife_caution(self, engine):
        """Sharp utensil → caution."""
        detections = [
            DetectionResult(
                category=ObjectCategory.UTENSIL,
                confidence=0.7,
                bbox=[0.4, 0.5, 0.6, 0.8],
                zone=Zone.CENTER,
                label="knife",
            )
        ]
        cmd = engine.decide(detections)
        assert "knife" in cmd.message.lower() or "sharp" in cmd.message.lower()

    def test_sports_center_caution(self, engine):
        """Sports equipment in center → caution."""
        detections = [
            DetectionResult(
                category=ObjectCategory.SPORTS,
                confidence=0.75,
                bbox=[0.4, 0.5, 0.6, 0.8],
                zone=Zone.CENTER,
                label="skateboard",
            )
        ]
        cmd = engine.decide(detections)
        assert "skateboard" in cmd.message.lower()

    def test_window_center_caution(self, engine):
        """Window in center → caution about glass."""
        detections = [_det(ObjectCategory.WINDOW, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert "window" in cmd.message.lower() or "glass" in cmd.message.lower()

    def test_appliance_center_blocks(self, engine):
        """Appliance in center → navigate around."""
        detections = [_det(ObjectCategory.APPLIANCE, Zone.CENTER)]
        cmd = engine.decide(detections)
        assert cmd.action in (NavigationAction.MOVE_LEFT, NavigationAction.MOVE_RIGHT)

    def test_vehicle_priority_over_animal(self, engine):
        """Vehicle has higher priority than animal."""
        detections = [
            _det(ObjectCategory.VEHICLE, Zone.CENTER, bbox=[0.1, 0.1, 0.9, 0.9]),
            _det(ObjectCategory.ANIMAL, Zone.LEFT),
        ]
        cmd = engine.decide(detections)
        assert cmd.action == NavigationAction.STOP
        assert "vehicle" in cmd.message.lower()
