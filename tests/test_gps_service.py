"""
Tests for the GPS Service.
"""

import pytest

from backend.models.schemas import GPSCoordinates
from backend.services.gps_service import GPSService


@pytest.fixture
def gps():
    return GPSService()


@pytest.fixture
def sample_coords():
    return GPSCoordinates(
        latitude=28.6139,
        longitude=77.2090,
        accuracy=10.0,
        altitude=220.0,
        timestamp=1700000000.0,
    )


class TestGPSService:
    def test_initial_state(self, gps):
        assert not gps.is_active
        assert gps.last_coordinates is None

    def test_update_coordinates(self, gps, sample_coords):
        gps.update_coordinates(sample_coords)
        assert gps.is_active
        assert gps.last_coordinates.latitude == 28.6139

    def test_maps_link(self, gps, sample_coords):
        gps.update_coordinates(sample_coords)
        link = gps.generate_maps_link()
        assert "google.com/maps" in link
        assert "28.6139" in link
        assert "77.209" in link

    def test_emergency_alert(self, gps, sample_coords):
        gps.update_coordinates(sample_coords)
        alert = gps.generate_emergency_alert()
        assert alert is not None
        assert "Emergency" in alert.message
        assert "google.com/maps" in alert.maps_link

    def test_emergency_no_gps(self, gps):
        assert gps.generate_emergency_alert() is None

    def test_share_text(self, gps, sample_coords):
        gps.update_coordinates(sample_coords)
        text = gps.generate_share_location_text()
        assert "Emergency" in text
        assert "28.613900" in text

    def test_deactivate(self, gps, sample_coords):
        gps.update_coordinates(sample_coords)
        assert gps.is_active
        gps.deactivate()
        assert not gps.is_active
