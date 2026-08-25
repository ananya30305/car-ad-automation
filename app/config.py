"""Central configuration loaded from environment / .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
RAW_DIR = DATA_DIR / "raw"
VEHICLES_DIR = DATA_DIR / "vehicles"
CANONICAL_DIR = DATA_DIR / "canonical"
READY_DIR = DATA_DIR / "ready"
REJECTED_DIR = DATA_DIR / "rejected"
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", DATA_DIR / "images")).resolve()
REPORTS_DIR = DATA_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"
FORM_MAP_PATH = Path(os.getenv("FORM_MAP_PATH", CONFIG_DIR / "form_map.json")).resolve()
DROPDOWN_MAP_PATH = Path(
    os.getenv("DROPDOWN_MAP_PATH", CONFIG_DIR / "dropdown_map.json")
).resolve()

DESTINATION_POST_URL = os.getenv(
    "DESTINATION_POST_URL",
    "https://august2026karnataka.dicewebfreelancers.com/index.php/post-free-ad",
)
DESTINATION_BASE_URL = os.getenv(
    "DESTINATION_BASE_URL",
    "https://august2026karnataka.dicewebfreelancers.com",
)

HEADLESS = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes"}
MAX_ADS = int(os.getenv("MAX_ADS", "50"))
REQUIRED_IMAGES = int(os.getenv("REQUIRED_IMAGES", "5"))
MIN_FEATURES = int(os.getenv("MIN_FEATURES", "3"))
MIN_HIGHLIGHTS = int(os.getenv("MIN_HIGHLIGHTS", "1"))
PAGE_TIMEOUT_MS = int(os.getenv("PAGE_TIMEOUT_MS", "60000"))
BROWSER_PROFILE_DIR = Path(
    os.getenv("BROWSER_PROFILE_DIR", BASE_DIR / "browser_profile")
).resolve()

# Optional inventory input (converted into the same canonical schema)
INVENTORY_JSON = DATA_DIR / "inventory.json"
INVENTORY_CSV = DATA_DIR / "inventory.csv"

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Fixed destination category path (inspected via public AJAX APIs)
CATEGORY_PATH_LABELS = [
    "Vehicles",
    "Cars - Parts",
    "Used cars in South Africa",
]


def ensure_directories() -> None:
    for path in (
        RAW_DIR,
        VEHICLES_DIR,
        CANONICAL_DIR,
        READY_DIR,
        REJECTED_DIR,
        IMAGE_DIR,
        REPORTS_DIR,
        CONFIG_DIR,
        BROWSER_PROFILE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
