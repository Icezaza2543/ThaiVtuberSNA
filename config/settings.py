"""
Thai VTuber Audience Network (SNA)
Configuration Settings
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EVENTS_DIR = DATA_DIR / "events"
ANALYTICS_DIR = DATA_DIR / "analytics"
CACHE_DIR = DATA_DIR / "cache"

for directory in [DATA_DIR, EVENTS_DIR, ANALYTICS_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Privacy & Hashing
# Persistent HMAC Secret Key location
SECRET_KEY_PATH = BASE_DIR / "config" / "secret.key"
SECRET_FINGERPRINT_PATH = BASE_DIR / "config" / "secret.fingerprint"
SALT_SECRET = os.getenv("VTUBER_SNA_SALT", "")

# Priority System - Subscriber Tiers
SUBSCRIBER_TIERS = {
    "S": 100_000,
    "A": 50_000,
    "B": 10_000,
    "C": 1_000,
    "D": 0
}

# Scheduler Weights (Multi-objective optimization)
# Default weights: fitness = 0.60 * sub + 0.20 * gap + 0.10 * live + 0.10 * recency
SCHEDULER_WEIGHTS = {
    "subscriber_priority": float(os.getenv("WEIGHT_SUBSCRIBER", 0.60)),
    "data_gap": float(os.getenv("WEIGHT_DATA_GAP", 0.20)),
    "live_urgency": float(os.getenv("WEIGHT_LIVE_URGENCY", 0.10)),
    "collection_recency": float(os.getenv("WEIGHT_RECENCY", 0.10))
}

# First Filter Rules
FILTER_RULES = {
    "min_thai_confidence": 0.5,
    "min_subscribers": 100,
    "dormant_days_threshold": 90,
    "thai_keywords": [
        "vtuber", "วีทูปเบอร์", "วีทูป", "virtual youtuber", "th", "ไทย", "thailand",
        "live2d", "3d", "สายเลือดไทย", "สังกัด"
    ]
}

# Google Sheets Configuration
GOOGLE_SHEETS_CONFIG = {
    "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(BASE_DIR / "credentials.json")),
    "spreadsheet_id": os.getenv("VTUBER_SPREADSHEET_ID", ""),
    "sheet_vtubers": "VTUBERS",
    "sheet_system": "SYSTEM",
    "sheet_network": "NETWORK_RESULT",
    "local_fallback_path": DATA_DIR / "registry_vtubers.csv"
}

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Worker Configuration
DEFAULT_WORKERS = int(os.getenv("MAX_COLLECTOR_WORKERS", 3))
