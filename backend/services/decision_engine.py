"""
Navigation Decision Engine.

Implements the core decision logic:
  - Obstacle detected → determine free direction
  - Stairs detected → warn user
  - Vehicle approaching → alert user
  - Path clear → go straight

Priority system ensures the most critical instruction is spoken.
"""

from __future__ import annotations

import logging
from typing import List

from backend.models.schemas import (
    DetectionResult,
    FrameAnalysis,
    NavigationAction,
    NavigationCommand,
    ObjectCategory,
    Zone,
)

logger = logging.getLogger(__name__)

# Priority levels
PRIORITY_CLEAR = 0
PRIORITY_INFO = 2
PRIORITY_CAUTION = 5
PRIORITY_WARNING = 7
PRIORITY_CRITICAL = 9


class DecisionEngine:
    """
    Stateless decision engine.
    Takes a list of detections and produces a single NavigationCommand.
    """

    def decide(self, detections: List[DetectionResult]) -> NavigationCommand:
        """
        Analyze all detections and produce the highest-priority navigation
        command.
        """
        if not detections:
            return NavigationCommand(
                action=NavigationAction.GO_STRAIGHT,
                message="Path is clear. Go straight.",
                priority=PRIORITY_CLEAR,
                speak=True,
            )

        commands: List[NavigationCommand] = []

        # --- Classify what's in each zone ---
        left_blocked = False
        center_blocked = False
        right_blocked = False
        zones_occupied = {Zone.LEFT: [], Zone.CENTER: [], Zone.RIGHT: []}

        for det in detections:
            zones_occupied[det.zone].append(det)
            if det.zone == Zone.LEFT:
                left_blocked = True
            elif det.zone == Zone.CENTER:
                center_blocked = True
            elif det.zone == Zone.RIGHT:
                right_blocked = True

        # --- Check for vehicles (highest urgency) ---
        vehicles = [d for d in detections if d.category == ObjectCategory.VEHICLE]
        if vehicles:
            best_vehicle = max(vehicles, key=lambda v: v.confidence)
            # Large bbox = close vehicle
            bbox_area = (best_vehicle.bbox[2] - best_vehicle.bbox[0]) * (
                best_vehicle.bbox[3] - best_vehicle.bbox[1]
            )
            if bbox_area > 0.15:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.STOP,
                        message="Vehicle very close! Stop immediately!",
                        priority=PRIORITY_CRITICAL,
                        speak=True,
                    )
                )
            else:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message="Vehicle approaching. Stay alert.",
                        priority=PRIORITY_WARNING,
                        speak=True,
                    )
                )

        # --- Check for stairs ---
        stairs = [d for d in detections if d.category == ObjectCategory.STAIRS]
        if stairs:
            commands.append(
                NavigationCommand(
                    action=NavigationAction.CAUTION,
                    message="Stairs ahead. Proceed with caution.",
                    priority=PRIORITY_WARNING,
                    speak=True,
                )
            )

        # --- Check for potholes ---
        potholes = [d for d in detections if d.category == ObjectCategory.POTHOLE]
        if potholes:
            for p in potholes:
                if p.zone == Zone.CENTER:
                    if not left_blocked:
                        commands.append(
                            NavigationCommand(
                                action=NavigationAction.MOVE_LEFT,
                                message="Pothole ahead. Move left.",
                                priority=PRIORITY_WARNING,
                                speak=True,
                            )
                        )
                    elif not right_blocked:
                        commands.append(
                            NavigationCommand(
                                action=NavigationAction.MOVE_RIGHT,
                                message="Pothole ahead. Move right.",
                                priority=PRIORITY_WARNING,
                                speak=True,
                            )
                        )
                    else:
                        commands.append(
                            NavigationCommand(
                                action=NavigationAction.STOP,
                                message="Pothole ahead. No clear path. Stop.",
                                priority=PRIORITY_CRITICAL,
                                speak=True,
                            )
                        )
                elif p.zone == Zone.LEFT:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.CAUTION,
                            message="Pothole on your left.",
                            priority=PRIORITY_CAUTION,
                            speak=True,
                        )
                    )
                elif p.zone == Zone.RIGHT:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.CAUTION,
                            message="Pothole on your right.",
                            priority=PRIORITY_CAUTION,
                            speak=True,
                        )
                    )

        # --- General obstacle / person / wall in center ---
        center_obstacles = [
            d
            for d in zones_occupied[Zone.CENTER]
            if d.category
            in (
                ObjectCategory.OBSTACLE,
                ObjectCategory.PERSON,
                ObjectCategory.WALL,
            )
        ]
        if center_obstacles:
            # Determine which direction is free
            if not left_blocked and not right_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_LEFT,
                        message="Obstacle ahead. Move left.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            elif not left_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_LEFT,
                        message="Obstacle ahead, right side blocked. Move left.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            elif not right_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_RIGHT,
                        message="Obstacle ahead, left side blocked. Move right.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            else:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.STOP,
                        message="Path blocked on all sides. Stop.",
                        priority=PRIORITY_CRITICAL,
                        speak=True,
                    )
                )

        # --- Persons nearby (informational) ---
        persons = [
            d
            for d in detections
            if d.category == ObjectCategory.PERSON and d.zone != Zone.CENTER
        ]
        if persons and not commands:
            commands.append(
                NavigationCommand(
                    action=NavigationAction.GO_STRAIGHT,
                    message="Person nearby. Path is clear, go straight.",
                    priority=PRIORITY_INFO,
                    speak=True,
                )
            )

        # If no specific command generated, path is clear
        if not commands:
            return NavigationCommand(
                action=NavigationAction.GO_STRAIGHT,
                message="Path is clear. Go straight.",
                priority=PRIORITY_CLEAR,
                speak=True,
            )

        # Return highest-priority command
        commands.sort(key=lambda c: c.priority, reverse=True)
        return commands[0]

    def analyze_frame(
        self,
        detections: List[DetectionResult],
        frame_id: int = 0,
        timestamp: float = 0.0,
        fps: float = 0.0,
    ) -> FrameAnalysis:
        """Build a complete FrameAnalysis with command."""
        command = self.decide(detections)
        return FrameAnalysis(
            frame_id=frame_id,
            timestamp=timestamp,
            detections=detections,
            command=command,
            fps=fps,
        )
