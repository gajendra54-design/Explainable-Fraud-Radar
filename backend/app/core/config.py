import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + str(ROOT / "radar.db"))
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", str(ROOT / "artifacts")))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
ALERT_THRESHOLD = float(os.environ["ALERT_THRESHOLD"]) if os.getenv("ALERT_THRESHOLD") else None
