"""
FastAPI Application – AR Navigation System Backend.

Provides:
  - WebSocket endpoint for real-time frame processing
  - REST endpoints for status, emergency alerts, GPS
  - Static file serving for the frontend
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import config
from backend.models.schemas import GPSCoordinates, WebSocketMessage
from backend.services.frame_processor import FrameProcessor

# Logging setup
logging.basicConfig(
    level=getattr(logging, config.server.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global processor instance
processor = FrameProcessor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle."""
    logger.info("=== AR Navigation System Starting ===")
    processor.initialize()
    logger.info("=== System Ready ===")
    yield
    logger.info("=== Shutting Down ===")
    processor.shutdown()


app = FastAPI(
    title="AR Navigation System",
    description="Real-time obstacle detection and navigation guidance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Frontend ───────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── REST Endpoints ────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the frontend app."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "AR Navigation System API", "docs": "/docs"})


@app.get("/api/status")
async def get_status():
    """Get system health status."""
    return processor.get_status()


@app.post("/api/gps")
async def update_gps(coords: GPSCoordinates):
    """Update GPS coordinates."""
    processor.update_gps(coords)
    return {"status": "ok", "maps_link": processor.gps.generate_maps_link(coords)}


@app.post("/api/emergency")
async def emergency_alert():
    """Trigger emergency alert with current location."""
    alert = processor.gps.generate_emergency_alert()
    if alert is None:
        raise HTTPException(status_code=400, detail="No GPS data available")
    return alert.model_dump()


@app.get("/api/location")
async def get_location():
    """Get current location info."""
    coords = processor.gps.last_coordinates
    if coords is None:
        return {"active": False, "message": "No GPS data"}
    return {
        "active": True,
        "coordinates": coords.model_dump(),
        "maps_link": processor.gps.generate_maps_link(),
        "share_text": processor.gps.generate_share_location_text(),
    }


# ─── WebSocket Endpoint ────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Real-time WebSocket connection for frame processing.

    Messages from client:
      - Binary: raw JPEG frame data
      - Text JSON: {"type": "frame", "data": {"image": "<base64>"}}
      - Text JSON: {"type": "gps", "data": {"latitude": ..., "longitude": ...}}
      - Text JSON: {"type": "emergency"}

    Messages to client:
      - JSON: FrameAnalysis result
      - JSON: Emergency alert
      - JSON: Status updates
    """
    await ws.accept()
    client_id = id(ws)
    logger.info("WebSocket client connected: %s", client_id)

    try:
        # Send initial status
        status = processor.get_status()
        await ws.send_json({"type": "status", "data": status})

        while True:
            # Handle both binary and text messages
            message = await ws.receive()

            if "bytes" in message and message["bytes"]:
                # Binary frame data (JPEG)
                frame_data = message["bytes"]
                analysis = processor.process_frame_bytes(frame_data)
                if analysis:
                    await ws.send_json({
                        "type": "analysis",
                        "data": analysis.model_dump(),
                    })

            elif "text" in message and message["text"]:
                try:
                    msg = json.loads(message["text"])
                    msg_type = msg.get("type", "")
                    msg_data = msg.get("data", {})

                    if msg_type == "frame":
                        # Base64 encoded frame
                        b64 = msg_data.get("image", "")
                        if b64:
                            analysis = processor.process_base64_frame(b64)
                            if analysis:
                                await ws.send_json({
                                    "type": "analysis",
                                    "data": analysis.model_dump(),
                                })

                    elif msg_type == "gps":
                        coords = GPSCoordinates(**msg_data)
                        processor.update_gps(coords)
                        await ws.send_json({
                            "type": "gps_ack",
                            "data": {
                                "maps_link": processor.gps.generate_maps_link(coords)
                            },
                        })

                    elif msg_type == "emergency":
                        alert = processor.gps.generate_emergency_alert()
                        if alert:
                            await ws.send_json({
                                "type": "emergency",
                                "data": alert.model_dump(),
                            })
                        else:
                            await ws.send_json({
                                "type": "error",
                                "data": {"message": "No GPS data for emergency"},
                            })

                    elif msg_type == "status":
                        await ws.send_json({
                            "type": "status",
                            "data": processor.get_status(),
                        })

                except json.JSONDecodeError:
                    await ws.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: %s", client_id)
    except Exception as e:
        logger.error("WebSocket error for client %s: %s", client_id, e)
        try:
            await ws.close()
        except Exception:
            pass
