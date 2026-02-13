"""
GPS Processing Service.

Receives GPS coordinates from the frontend (mobile device),
generates Google Maps links, and handles emergency alerts.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Optional

from backend.config import config
from backend.models.schemas import EmergencyAlert, GPSCoordinates

logger = logging.getLogger(__name__)


class GPSService:
    """GPS data processing and emergency alert generation."""

    def __init__(self) -> None:
        self._cfg = config.gps
        self._last_coords: Optional[GPSCoordinates] = None
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def last_coordinates(self) -> Optional[GPSCoordinates]:
        return self._last_coords

    def update_coordinates(self, coords: GPSCoordinates) -> None:
        """Update stored GPS coordinates from frontend."""
        self._last_coords = coords
        self._active = True
        logger.debug(
            "GPS updated: lat=%.6f, lon=%.6f, acc=%.1f",
            coords.latitude,
            coords.longitude,
            coords.accuracy or 0,
        )

    def generate_maps_link(
        self, coords: Optional[GPSCoordinates] = None
    ) -> str:
        """Generate a Google Maps link for the given or last-known coordinates."""
        c = coords or self._last_coords
        if c is None:
            return ""
        return (
            f"https://www.google.com/maps?q={c.latitude},{c.longitude}"
        )

    def generate_emergency_alert(
        self, coords: Optional[GPSCoordinates] = None
    ) -> Optional[EmergencyAlert]:
        """
        Generate an emergency alert with location info.
        Returns None if no GPS data is available.
        """
        c = coords or self._last_coords
        if c is None:
            logger.warning("Emergency alert requested but no GPS data available.")
            return None

        maps_link = self.generate_maps_link(c)
        message = f"{self._cfg.emergency_message} {maps_link}"

        alert = EmergencyAlert(
            message=message,
            coordinates=c,
            maps_link=maps_link,
            timestamp=time.time(),
        )

        logger.warning("EMERGENCY ALERT: %s", message)
        return alert

    def generate_share_location_text(
        self, coords: Optional[GPSCoordinates] = None
    ) -> str:
        """Generate shareable location text for SMS/messaging."""
        c = coords or self._last_coords
        if c is None:
            return "Location unavailable."

        maps_link = self.generate_maps_link(c)
        return (
            f"{self._cfg.emergency_message}\n"
            f"Location: {maps_link}\n"
            f"Coordinates: {c.latitude:.6f}, {c.longitude:.6f}\n"
            f"Accuracy: {c.accuracy or 'unknown'}m"
        )

    def deactivate(self) -> None:
        """Mark GPS as inactive."""
        self._active = False
