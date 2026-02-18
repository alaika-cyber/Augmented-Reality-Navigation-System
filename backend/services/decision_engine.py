"""
Navigation Decision Engine.

Implements the core decision logic:
  - Obstacle / furniture detected → determine free direction
  - Stairs detected → warn user
  - Vehicle approaching → alert user
  - Animal detected → caution / avoid
  - Glass / water / utensils → careful navigation
  - Door / window → informational awareness
  - Traffic signs → awareness alerts
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

# Categories that physically block the path
BLOCKING_CATEGORIES = {
    ObjectCategory.OBSTACLE,
    ObjectCategory.PERSON,
    ObjectCategory.WALL,
    ObjectCategory.FURNITURE,
    ObjectCategory.APPLIANCE,
    ObjectCategory.DOOR,
    ObjectCategory.PLANT,
}


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
            bbox_area = (best_vehicle.bbox[2] - best_vehicle.bbox[0]) * (
                best_vehicle.bbox[3] - best_vehicle.bbox[1]
            )
            if bbox_area > 0.15:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.STOP,
                        message=f"Vehicle very close! Stop immediately! ({best_vehicle.label})",
                        priority=PRIORITY_CRITICAL,
                        speak=True,
                    )
                )
            else:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Vehicle detected: {best_vehicle.label}. Stay alert.",
                        priority=PRIORITY_WARNING,
                        speak=True,
                    )
                )

        # --- Check for animals ---
        animals = [d for d in detections if d.category == ObjectCategory.ANIMAL]
        if animals:
            best_animal = max(animals, key=lambda a: a.confidence)
            bbox_area = (best_animal.bbox[2] - best_animal.bbox[0]) * (
                best_animal.bbox[3] - best_animal.bbox[1]
            )
            # Large animals (horse, cow, bear, etc.) are more dangerous
            large_animals = {"horse", "cow", "elephant", "bear", "zebra", "giraffe"}
            is_large = any(lbl in best_animal.label.lower() for lbl in large_animals)

            if is_large or bbox_area > 0.12:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.STOP,
                        message=f"Large animal ahead: {best_animal.label}! Stop and keep distance.",
                        priority=PRIORITY_CRITICAL,
                        speak=True,
                    )
                )
            elif best_animal.zone == Zone.CENTER:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Animal ahead: {best_animal.label}. Proceed with caution.",
                        priority=PRIORITY_WARNING,
                        speak=True,
                    )
                )
            else:
                side = "left" if best_animal.zone == Zone.LEFT else "right"
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Animal on your {side}: {best_animal.label}.",
                        priority=PRIORITY_CAUTION,
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

        # --- Check for water hazards ---
        water = [d for d in detections if d.category == ObjectCategory.WATER]
        if water:
            best_water = max(water, key=lambda w: w.confidence)
            if best_water.zone == Zone.CENTER:
                if not left_blocked:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.MOVE_LEFT,
                            message=f"Water ahead: {best_water.label}. Move left to avoid.",
                            priority=PRIORITY_WARNING,
                            speak=True,
                        )
                    )
                elif not right_blocked:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.MOVE_RIGHT,
                            message=f"Water ahead: {best_water.label}. Move right to avoid.",
                            priority=PRIORITY_WARNING,
                            speak=True,
                        )
                    )
                else:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.STOP,
                            message=f"Water ahead: {best_water.label}. No clear path. Stop.",
                            priority=PRIORITY_CRITICAL,
                            speak=True,
                        )
                    )
            else:
                side = "left" if best_water.zone == Zone.LEFT else "right"
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Water on your {side}: {best_water.label}.",
                        priority=PRIORITY_CAUTION,
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

        # --- Check for glass objects (breakable / sharp hazard) ---
        glass_objects = [d for d in detections if d.category == ObjectCategory.GLASS]
        if glass_objects:
            best_glass = max(glass_objects, key=lambda g: g.confidence)
            if best_glass.zone == Zone.CENTER:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Glass object ahead: {best_glass.label}. Be careful.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            else:
                side = "left" if best_glass.zone == Zone.LEFT else "right"
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Glass object on your {side}: {best_glass.label}.",
                        priority=PRIORITY_INFO,
                        speak=True,
                    )
                )

        # --- Check for utensils (sharp objects warning) ---
        utensils = [d for d in detections if d.category == ObjectCategory.UTENSIL]
        sharp_utensils = {"knife", "scissors"}
        if utensils:
            sharp = [u for u in utensils if any(s in u.label.lower() for s in sharp_utensils)]
            if sharp:
                best_sharp = max(sharp, key=lambda s: s.confidence)
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Sharp object detected: {best_sharp.label}. Be careful.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )

        # --- Check for traffic signs ---
        traffic = [d for d in detections if d.category == ObjectCategory.TRAFFIC_SIGN]
        if traffic:
            for t in traffic:
                if "stop sign" in t.label.lower():
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.STOP,
                            message="Stop sign detected. Stop and look around.",
                            priority=PRIORITY_WARNING,
                            speak=True,
                        )
                    )
                elif "traffic light" in t.label.lower():
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.CAUTION,
                            message="Traffic light ahead. Check signal before crossing.",
                            priority=PRIORITY_WARNING,
                            speak=True,
                        )
                    )
                elif "fire hydrant" in t.label.lower():
                    side = "left" if t.zone == Zone.LEFT else ("right" if t.zone == Zone.RIGHT else "ahead")
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.CAUTION,
                            message=f"Fire hydrant on your {side}.",
                            priority=PRIORITY_INFO,
                            speak=True,
                        )
                    )

        # --- Check for doors ---
        doors = [d for d in detections if d.category == ObjectCategory.DOOR]
        if doors:
            best_door = max(doors, key=lambda d: d.confidence)
            commands.append(
                NavigationCommand(
                    action=NavigationAction.CAUTION,
                    message=f"Door detected {best_door.zone.value} side. Watch for opening.",
                    priority=PRIORITY_CAUTION,
                    speak=True,
                )
            )

        # --- Check for windows (glass hazard) ---
        windows = [d for d in detections if d.category == ObjectCategory.WINDOW]
        if windows:
            for w in windows:
                if w.zone == Zone.CENTER:
                    commands.append(
                        NavigationCommand(
                            action=NavigationAction.CAUTION,
                            message="Glass window ahead. Be careful.",
                            priority=PRIORITY_CAUTION,
                            speak=True,
                        )
                    )

        # --- General blocking obstacles in center ---
        # (furniture, appliances, walls, obstacles, doors, plants, persons)
        center_obstacles = [
            d
            for d in zones_occupied[Zone.CENTER]
            if d.category in BLOCKING_CATEGORIES
        ]
        if center_obstacles:
            best_obs = max(center_obstacles, key=lambda o: o.confidence)
            label = best_obs.label or best_obs.category.value
            if not left_blocked and not right_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_LEFT,
                        message=f"{label} ahead. Move left.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            elif not left_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_LEFT,
                        message=f"{label} ahead, right side blocked. Move left.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )
            elif not right_blocked:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.MOVE_RIGHT,
                        message=f"{label} ahead, left side blocked. Move right.",
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

        # --- Electronics on the ground (tripping hazard) ---
        electronics = [
            d for d in detections
            if d.category == ObjectCategory.ELECTRONICS and d.zone == Zone.CENTER
        ]
        if electronics:
            best_elec = max(electronics, key=lambda e: e.confidence)
            # Only warn if it's low in the frame (likely on ground)
            if best_elec.bbox[3] > 0.7:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Object on the ground: {best_elec.label}. Watch your step.",
                        priority=PRIORITY_CAUTION,
                        speak=True,
                    )
                )

        # --- Food on path (informational/slip hazard) ---
        food_center = [
            d for d in zones_occupied[Zone.CENTER]
            if d.category == ObjectCategory.FOOD
        ]
        if food_center:
            commands.append(
                NavigationCommand(
                    action=NavigationAction.CAUTION,
                    message="Food item on the path. Watch your step.",
                    priority=PRIORITY_INFO,
                    speak=True,
                )
            )

        # --- Sports equipment on path ---
        sports_center = [
            d for d in zones_occupied[Zone.CENTER]
            if d.category == ObjectCategory.SPORTS
        ]
        if sports_center:
            best_sport = max(sports_center, key=lambda s: s.confidence)
            commands.append(
                NavigationCommand(
                    action=NavigationAction.CAUTION,
                    message=f"Sports equipment ahead: {best_sport.label}. Watch your step.",
                    priority=PRIORITY_CAUTION,
                    speak=True,
                )
            )

        # --- Personal items on path (tripping hazard) ---
        items_center = [
            d for d in zones_occupied[Zone.CENTER]
            if d.category == ObjectCategory.PERSONAL_ITEM
        ]
        if items_center:
            best_item = max(items_center, key=lambda i: i.confidence)
            # Only warn if low in frame
            if best_item.bbox[3] > 0.6:
                commands.append(
                    NavigationCommand(
                        action=NavigationAction.CAUTION,
                        message=f"Item on the path: {best_item.label}. Watch your step.",
                        priority=PRIORITY_INFO,
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
