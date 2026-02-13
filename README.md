# 🧭 Augmented Reality Navigation System

Real-time AI-powered navigation assistance with obstacle detection, voice guidance, and GPS emergency alerts. Designed for visually impaired users and pedestrian safety.

---

## 🎯 How It Works

```
Camera Sees → AI Decides → Voice Speaks
```

1. **App Opens** → Camera ON, GPS ON — no manual setup needed
2. **Live Monitoring** → AI continuously analyzes the camera feed
3. **Smart Navigation** → Voice tells you where to go

### Decision Logic

| Situation | Command |
|---|---|
| Path clear | "Go straight" |
| Obstacle ahead, left free | "Move left" |
| Obstacle ahead, right free | "Move right" |
| All sides blocked | "Stop" |
| Stairs detected | "Stairs ahead, proceed with caution" |
| Vehicle approaching | "Vehicle coming, stay alert" |
| Vehicle very close | "Stop immediately" |
| Pothole ahead | "Pothole ahead, move left/right" |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend (PWA)                  │
│  Camera → Frame Capture → WebSocket → AR Overlay │
│  GPS → Location Tracking → Emergency Alerts      │
│  Web Speech API → Voice Guidance                 │
└──────────────────┬──────────────────────────────┘
                   │ WebSocket (binary frames)
┌──────────────────▼──────────────────────────────┐
│               Backend (FastAPI)                  │
│  YOLOv8 Detection → Decision Engine → Response   │
│  GPS Processing → Emergency Alert Generation     │
│  TTS Service (pyttsx3 fallback)                  │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI + Uvicorn |
| **Object Detection** | YOLOv8 (Ultralytics) |
| **Computer Vision** | OpenCV |
| **AI Runtime** | PyTorch |
| **Voice (Server)** | pyttsx3 (offline) |
| **Voice (Client)** | Web Speech API |
| **Frontend** | Vanilla JS PWA |
| **Communication** | WebSocket (binary frames) |
| **GPS** | Browser Geolocation API |
| **Deployment** | Docker |

### Objects Detected

- 🚶 Person
- 🚗 Vehicle (car, bus, truck, motorcycle, bicycle)
- 🪜 Stairs (heuristic + custom model)
- 🧱 Wall (heuristic + custom model)
- ⚠️ Pothole (custom model)
- 🚧 Generic obstacles

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### 1. Clone & Install

```bash
git clone https://github.com/yashab-cyber/Augmented-Reality-Navigation-System.git
cd Augmented-Reality-Navigation-System

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
cp .env.example .env
# Edit .env to customize settings
```

### 3. Run

```bash
python run.py
```

Open **http://localhost:8000** on your phone or desktop browser.

> **Mobile Access:** Connect your phone to the same network and open `http://<your-ip>:8000`

### 4. Docker (Alternative)

```bash
docker compose up --build
```

---

## 📁 Project Structure

```
├── backend/
│   ├── __init__.py
│   ├── config.py                 # App configuration (env vars)
│   ├── main.py                   # FastAPI app + WebSocket handler
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── detection.py          # YOLOv8 object detection
│       ├── decision_engine.py    # Navigation logic
│       ├── tts_service.py        # Text-to-Speech
│       ├── gps_service.py        # GPS processing
│       └── frame_processor.py    # Pipeline orchestrator
├── frontend/
│   ├── index.html                # Main UI
│   ├── manifest.json             # PWA manifest
│   ├── css/
│   │   └── styles.css            # Full responsive styles
│   └── js/
│       ├── app.js                # Main app orchestrator
│       ├── camera.js             # Camera management
│       ├── websocket.js          # WebSocket client
│       ├── tts.js                # Client-side TTS
│       ├── gps.js                # GPS module
│       └── ar-renderer.js        # AR overlay renderer
├── tests/
│   ├── test_decision_engine.py   # Decision logic tests
│   ├── test_gps_service.py       # GPS service tests
│   └── test_api.py               # API endpoint tests
├── run.py                        # Entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container image
├── docker-compose.yml            # Container orchestration
├── .env.example                  # Environment template
└── .gitignore
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve frontend app |
| `GET` | `/api/status` | System health status |
| `POST` | `/api/gps` | Update GPS coordinates |
| `POST` | `/api/emergency` | Trigger emergency alert |
| `GET` | `/api/location` | Get current location info |

### WebSocket (`/ws`)

**Client → Server:**

| Format | Description |
|---|---|
| Binary (JPEG) | Camera frame for detection |
| `{"type": "frame", "data": {"image": "<base64>"}}` | Base64 frame |
| `{"type": "gps", "data": {"latitude": ..., "longitude": ...}}` | GPS update |
| `{"type": "emergency"}` | Emergency alert |
| `{"type": "status"}` | Request status |

**Server → Client:**

```json
{
  "type": "analysis",
  "data": {
    "frame_id": 42,
    "fps": 15.2,
    "detections": [
      {
        "category": "person",
        "confidence": 0.89,
        "bbox": [0.3, 0.2, 0.6, 0.9],
        "zone": "center",
        "label": "person"
      }
    ],
    "command": {
      "action": "move_left",
      "message": "Obstacle ahead. Move left.",
      "priority": 5,
      "speak": true
    }
  }
}
```

---

## 🧪 Testing

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## ⚙️ Configuration

All settings can be configured via environment variables or `.env` file:

| Variable | Default | Description |
|---|---|---|
| `SERVER_PORT` | `8000` | Server port |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | YOLOv8 model file |
| `YOLO_CONFIDENCE` | `0.45` | Detection threshold |
| `YOLO_DEVICE` | `cpu` | `cpu`, `cuda`, or `mps` |
| `FRAME_SKIP` | `2` | Process every Nth frame |
| `TTS_COOLDOWN` | `2.0` | Seconds between same voice messages |
| `CUSTOM_MODEL_PATH` |  | Path to custom model for stairs/pothole/wall |

### GPU Acceleration

```bash
# For NVIDIA GPU
YOLO_DEVICE=cuda python run.py

# For Apple Silicon
YOLO_DEVICE=mps python run.py
```

---

## 🔧 Custom Model Training

To improve stairs/pothole/wall detection, train a custom YOLOv8 model:

```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='custom_dataset.yaml',
    epochs=100,
    imgsz=640,
    classes=['stairs', 'wall', 'pothole', 'obstacle']
)
```

Then set `CUSTOM_MODEL_PATH=runs/detect/train/weights/best.pt` in your `.env`.

---

## 📱 Mobile Deployment

The frontend is a **Progressive Web App (PWA)**:

1. Open the app URL on your phone's browser
2. Tap "Add to Home Screen"
3. The app will run fullscreen like a native app
4. Camera and GPS permissions will be requested automatically

> **Note:** For camera access on mobile, the app must be served over HTTPS or localhost.

---

## 📄 License

MIT License