"""Legacy scraper pipeline runner.

DEPRECATED: This module is legacy code from the previous scraper implementation.
The new vehicle ad automation system does NOT scrape external websites. 
Per the project specification, the application operates ONLY on inventory data
explicitly provided by the user through authorized/licensed feeds.

This module is kept for backward compatibility only and should not be used
for new functionality. Use main.py instead for ad posting.
"""

import logging

from scraper import scrape


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    scrape()


if __name__ == "__main__":
    main()