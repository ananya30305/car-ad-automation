# config.py
# Configuration for the Vehicle Ad Automation project

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
BROWSER_PROFILE_DIR = BASE_DIR / "browser_profile"
REPORTS_DIR = BASE_DIR / "reports"
DEBUG_DIR = BASE_DIR / "debug"

# Create required folders automatically
for directory in [DATA_DIR, OUTPUT_DIR, LOG_DIR, CHECKPOINT_DIR, BROWSER_PROFILE_DIR, REPORTS_DIR, DEBUG_DIR]:
    directory.mkdir(exist_ok=True)

# ============================================================
# SOURCE DATA SETTINGS
# ============================================================

# Source inventory file - CSV or JSON
# The system will auto-detect which format exists
SOURCE_CSV = DATA_DIR / "inventory.csv"
SOURCE_JSON = DATA_DIR / "inventory.json"

# ============================================================
# DESTINATION WEBSITE SETTINGS
# ============================================================

# Destination URL for posting ads
DESTINATION_POST_URL = os.getenv(
    "DESTINATION_POST_URL",
    "https://august2026karnataka.dicewebfreelancers.com/index.php/post-free-ad"
)

# ============================================================
# BROWSER SETTINGS
# ============================================================

# Headless mode (set to False to see browser)
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

# Browser type
BROWSER = "chromium"

# Browser timeouts (milliseconds)
PAGE_TIMEOUT = 30_000  # 30 seconds
NAVIGATION_TIMEOUT = 30_000
ELEMENT_TIMEOUT = 10_000

# ============================================================
# PROCESSING SETTINGS
# ============================================================

# Batch size for processing
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))

# Maximum retries for transient errors
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Delay between retries (seconds)
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))

# Delay between requests (seconds)
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))

# ============================================================
# SUBMISSION SETTINGS
# ============================================================

# Dry run mode - fill form but don't submit
DRY_RUN = os.getenv("DRY_RUN", "True").lower() == "true"

# Enable actual submission
SUBMIT_AD = os.getenv("SUBMIT_AD", "False").lower() == "true"

# Require explicit confirmation before submission
CONFIRM_SUBMISSION = os.getenv("CONFIRM_SUBMISSION", "False").lower() == "true"

# ============================================================
# IMAGE SETTINGS
# ============================================================

# Maximum number of images to upload
IMAGE_LIMIT = int(os.getenv("IMAGE_LIMIT", "10"))

# Supported image formats
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}

# Maximum image file size (bytes)
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB

# Minimum images required (0 = error, 1-4 = warning, 5+ = OK)
MIN_IMAGES = int(os.getenv("MIN_IMAGES", "1"))
RECOMMENDED_IMAGES = int(os.getenv("RECOMMENDED_IMAGES", "5"))

# Image download directory (for form_filler fallback compatibility)
IMAGE_DOWNLOAD_DIR = DATA_DIR / "images"

# ============================================================
# VALIDATION SETTINGS
# ============================================================

# Require minimum fields
REQUIRE_TITLE = True
REQUIRE_PRICE = True
REQUIRE_DESCRIPTION = True

# Minimum description length (characters)
MIN_DESCRIPTION_LENGTH = 50

# ============================================================
# CHECKPOINT SETTINGS
# ============================================================

# Checkpoint file for resumable processing
CHECKPOINT_FILE = CHECKPOINT_DIR / "checkpoint.json"

# Auto-save checkpoint every N records
CHECKPOINT_INTERVAL = 1

# ============================================================
# LOGGING SETTINGS
# ============================================================

# Log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Log directory
LOG_DIRECTORY = LOG_DIR

# Save debug HTML on form errors
SAVE_DEBUG_HTML = os.getenv("SAVE_DEBUG_HTML", "True").lower() == "true"

# ============================================================
# FEATURE FLAGS
# ============================================================

# Enable deduplication checking
ENABLE_DEDUPLICATION = True

# Enable image validation
ENABLE_IMAGE_VALIDATION = True

# Enable form verification
ENABLE_FORM_VERIFICATION = True

# ============================================================
# LEGACY SCRAPER SETTINGS (Backward Compatibility Only)
# ============================================================
# NOTE: The new vehicle ad automation system does NOT scrape
# external websites. These variables are for backward compatibility
# with legacy scraper.py code only. They should not be used for
# new functionality.
#
# Per the project specification:
# "Do NOT scrape, copy, reproduce, or republish listings, images,
#  descriptions... unless the data is supplied through an explicitly
#  authorized/licensed feed. The application must operate ONLY on
#  inventory data that I provide."

# Legacy scraper base URL (Cars.co.za search template)
# Format string with {page} placeholder for pagination
BASE_URL = os.getenv(
    "BASE_URL",
    "https://www.cars.co.za/search/?Type=used&Page={page}"
)

# Maximum listings to scrape (legacy scraper)
MAX_LISTINGS = int(os.getenv("MAX_LISTINGS", "100"))

# HTTP request timeout (seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# User-Agent header for HTTP requests
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================
# CATEGORY SETTINGS
# ============================================================

# Expected category structure (may need adjustment based on actual site)
EXPECTED_CATEGORIES = [
    "Vehicles",
    "Cars",
    "Used Cars"
]


# ============================================================
# SCRAPING RULES
# ============================================================

# Sponsored listings must NOT be collected.
SKIP_SPONSORED = True


# We only want unique vehicle listings.
REMOVE_DUPLICATES = True


# ============================================================
# USER-AGENT
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)