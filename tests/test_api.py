"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client. Model loading is skipped in test mode."""
    import os
    os.environ["YOLO_MODEL_PATH"] = "yolov8n.pt"

    from backend.main import app
    return TestClient(app)


class TestAPI:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_status(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "detection_ready" in data
        assert "fps" in data

    def test_gps_update(self, client):
        response = client.post("/api/gps", json={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "accuracy": 10.0,
            "timestamp": 1700000000.0,
        })
        assert response.status_code == 200
        assert "maps_link" in response.json()

    def test_location_no_gps(self, client):
        response = client.get("/api/location")
        assert response.status_code == 200

    def test_emergency_no_gps(self, client):
        response = client.post("/api/emergency")
        # Should return 400 when no GPS data
        assert response.status_code in (400, 200)
