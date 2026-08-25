"""Resumable, rate-limited Cars.co.za collection pipeline.

DEPRECATED: This module is legacy code from the previous scraper implementation.
The new vehicle ad automation system does NOT scrape external websites. 
Per the project specification, the application operates ONLY on inventory data
explicitly provided by the user through authorized/licensed feeds.

This module is kept for backward compatibility only and should not be used
for new functionality. Use batch_processor.py instead for ad posting.
"""

import logging
from pathlib import Path

# For backward compatibility, provide the config imports that this module originally used
from config import DATA_DIR, MAX_LISTINGS, MAX_RETRIES, REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT, BASE_URL

LOG_PATH = Path(__file__).resolve().parent / "logs" / "scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Legacy utility function - kept for import compatibility."""
    return url.rstrip('/').lower() if url else ""


def deduplicate(records: list) -> tuple[list, int]:
    """
    Legacy function - kept for import compatibility.
    
    DEPRECATED: Use deduplicator.py module instead for new code.
    
    Returns:
        (records, 0) - Returns records unchanged with 0 duplicates found.
    """
    return records, 0


def scrape(*args, **kwargs):
    """
    Legacy scrape function.
    
    DEPRECATED: Do not use. The new system does not scrape external websites.
    
    Raises:
        NotImplementedError: Always, as scraping is not supported in the new architecture.
    """
    raise NotImplementedError(
        "\n" + "="*70 +
        "\nSCRAPING IS NOT SUPPORTED IN THE NEW SYSTEM\n" +
        "="*70 +
        "\n\nThe scraper.py module is deprecated and disabled.\n\n"
        "Per the project specification:\n"
        "  'Do NOT scrape, copy, reproduce, or republish listings, images,\n"
        "   descriptions... unless the data is supplied through an explicitly\n"
        "   authorized/licensed feed. The application must operate ONLY on\n"
        "   inventory data that I provide.'\n\n"
        "To post advertisements using YOUR authorized inventory:\n"
        "  1. Prepare inventory in: data/inventory.json or data/inventory.csv\n"
        "  2. Run: python main.py --help\n"
        "  3. Test: python main.py --batch 3 --dry-run\n"
        "  4. Post: python main.py --batch 10 --submit --confirm\n\n" +
        "="*70 + "\n"
    )


def main() -> None:
    """Entry point for legacy scraper."""
    raise NotImplementedError(
        "Scraping is not supported. Use: python main.py --help"
    )


if __name__ == "__main__":
    main()
