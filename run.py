# ============================================================
# AR Navigation System – Entry Point
# ============================================================
"""
Usage:
    python run.py
    
Or with uvicorn directly:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import uvicorn
    from backend.config import config

    print("=" * 60)
    print("  AR Navigation System")
    print("=" * 60)
    print(f"  Server:  http://{config.server.host}:{config.server.port}")
    print(f"  Model:   {config.detection.model_path}")
    print(f"  Device:  {config.detection.device}")
    print(f"  Log:     {config.server.log_level}")
    print("=" * 60)

    uvicorn.run(
        "backend.main:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        reload=False,
        ws_max_size=config.server.ws_max_size,
    )


if __name__ == "__main__":
    main()
