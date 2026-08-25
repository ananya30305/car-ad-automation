"""Resumable, rate-limited Cars.co.za collection pipeline.

DEPRECATED: This module is legacy code from the previous scraper implementation.
The new vehicle ad automation system does NOT scrape external websites. 
Per the project specification, the application operates ONLY on inventory data
explicitly provided by the user through authorized/licensed feeds.

This module is kept for backward compatibility only and should not be used
for new functionality. Use batch_processor.py instead for ad posting.
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from config import BASE_URL, DATA_DIR, MAX_LISTINGS, MAX_RETRIES, REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT
from deduplicator import deduplicate, normalize_url
from exporter import export_form_ready
from image_downloader import attach_downloaded_images
from parser import parse_listing
from storage import save_dataset, save_vehicle
from validator import validate_records

LOG_PATH = Path(__file__).resolve().parent / "logs" / "scraper.log"
RAW_PATH = DATA_DIR / "cars_raw.json"
VALID_PATH = DATA_DIR / "cars_validated.json"
INVALID_PATH = DATA_DIR / "cars_invalid.json"
IMAGES_PATH = DATA_DIR / "cars_images.json"
REPORT_PATH = DATA_DIR / "scraping_report.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()])
logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Ignoring unreadable JSON file: %s", path)
        return []
    return value if isinstance(value, list) else []


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-ZA,en;q=0.8", "Referer": "https://www.cars.co.za/"})
    retry = Retry(total=MAX_RETRIES, connect=MAX_RETRIES, read=MAX_RETRIES, status=MAX_RETRIES, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset({"GET"}), raise_on_status=False)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch(session: requests.Session, url: str) -> str:
    logger.info("Downloading %s", url)
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def find_listing_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/for-sale/used/"]'):
        href = anchor.get("href")
        if not href:
            continue
        url = normalize_url(urljoin("https://www.cars.co.za/", href))
        if re.search(r"/for-sale/used/.+/\d+/?$", url) and url not in seen:
            seen.add(url)
            links.append(url)
    return links


def scrape(target: int = MAX_LISTINGS, max_pages: int = 0, start_page: int = 1, fresh: bool = False) -> dict[str, Any]:
    started_at = utc_now()
    existing_valid = [] if fresh else load_records(VALID_PATH)
    existing_raw = [] if fresh else load_records(RAW_PATH)
    processed_urls = {normalize_url(str(record.get("source_url"))) for record in existing_raw + existing_valid if record.get("source_url")}
    records = list(existing_raw)
    duplicates = 0
    failures = 0
    session = build_session()
    page = start_page
    pages_without_new_links = 0
    try:
        while len(existing_valid) < target and (not max_pages or page < start_page + max_pages):
            search_url = BASE_URL.format(page=page)
            try:
                links = find_listing_links(fetch(session, search_url))
            except requests.RequestException as error:
                logger.error("Search page %d failed: %s", page, error)
                break
            if not links:
                pages_without_new_links += 1
                if pages_without_new_links >= 2:
                    break
                page += 1
                continue
            new_links = [link for link in links if link not in processed_urls]
            new_links = new_links[:max(0, target - len(existing_valid))]
            if not new_links:
                pages_without_new_links += 1
            else:
                pages_without_new_links = 0
            for url in new_links:
                if len(existing_valid) >= target:
                    break
                processed_urls.add(url)
                try:
                    record = parse_listing(fetch(session, url), url)
                    record["scraped_at"] = utc_now()
                    record = attach_downloaded_images(record, session)
                    records.append(record)
                    save_vehicle(record)
                    logger.info("[%d/%d] %s | Price: %s | Images: %d/5 | Status: parsed", len(records), target, record.get("title") or "untitled", record.get("price") or "missing", len(record.get("images") or []))
                except (requests.RequestException, ValueError, RuntimeError) as error:
                    failures += 1
                    logger.error("Listing failed (%s): %s", url, error)
                time.sleep(REQUEST_DELAY)
            unique_records, found_duplicates = deduplicate(records)
            duplicates += found_duplicates
            records = unique_records
            valid, invalid = validate_records(records)
            existing_valid = valid
            save_json(RAW_PATH, records)
            save_json(VALID_PATH, valid)
            save_json(INVALID_PATH, invalid)
            save_json(IMAGES_PATH, [{"source_url": item.get("source_url"), "images": item.get("images", [])} for item in records])
            export_form_ready(valid, DATA_DIR / "form_ready_ads.json")
            page += 1
    finally:
        report = {"target": target, "unique_listings_found": len(records), "valid_listings": len(existing_valid), "invalid_listings": len(load_records(INVALID_PATH)), "duplicate_listings": duplicates, "listings_missing_images": sum(len(item.get("images") or []) < 5 for item in records), "listings_with_less_than_5_images": sum(len(item.get("images") or []) < 5 for item in records), "request_failures": failures, "started_at": started_at, "finished_at": utc_now()}
        all_records = existing_valid + load_records(INVALID_PATH)
        save_dataset(all_records, report)
        save_json(REPORT_PATH, report)
        logger.info("Finished: %d valid, %d invalid, %d unique", report["valid_listings"], report["invalid_listings"], report["unique_listings_found"])
    return report


def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Collect and validate Cars.co.za used-car listings.")
    argument_parser.add_argument("--limit", type=int, default=MAX_LISTINGS)
    argument_parser.add_argument("--max-pages", type=int, default=0)
    argument_parser.add_argument("--start-page", type=int, default=1)
    argument_parser.add_argument("--fresh", action="store_true")
    args = argument_parser.parse_args()
    scrape(args.limit, args.max_pages, args.start_page, args.fresh)


if __name__ == "__main__":
    main()
