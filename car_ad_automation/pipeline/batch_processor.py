"""
Batch Processor - Standalone Browser Automation for Manual Ad Posting.

====================================================================
USAGE CONTEXT - IMPORTANT
====================================================================

This module provides a STANDALONE browser automation workflow for
interactive manual ad posting. It reads pre-built ads from
ads_ready_for_form.json and lets you manually approve each submission.

This is DIFFERENT from the main Pipeline class in pipeline.py:

  - Pipeline (pipeline.py): Complete end-to-end automation
    * Loads source data (CSV/JSON/scraper)
    * Normalizes, validates, deduplicates
    * Builds descriptions, validates images
    * Posts ads automatically (or dry-run)
    * Uses checkpoint/resume
    * Entry point: python -m car_ad_automation.cli.main

  - BatchProcessor (this file): Manual interactive posting only
    * Requires pre-built ads_ready_for_form.json
    * You manually navigate to form page
    * You manually click "Post" for each ad
    * No checkpoint/resume
    * Entry point: python -m car_ad_automation.pipeline.batch_processor

Use Pipeline for production automation. Use BatchProcessor for
testing form filling or when you need manual control over each post.
"""

import json
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

from car_ad_automation.stages.post.form_filler import RobustFormFiller
from car_ad_automation.stages.build.category_handler import DynamicCategoryCascader
from car_ad_automation.core.config import OUTPUT_DIR, BROWSER_PROFILE_DIR

PROFILE_DIR = BROWSER_PROFILE_DIR
ADS_FILE = OUTPUT_DIR / "ads_ready_for_form.json"
TARGET_PORTAL_URL = "https://august2026karnataka.dicewebfreelancers.com/index.php/my-ads"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def run_batch():
    if not ADS_FILE.exists():
        logger.error(f"Ad file not found: {ADS_FILE}")
        return

    ads = json.loads(ADS_FILE.read_text(encoding="utf-8"))
    if not ads:
        logger.error("No advertisements found in file!")
        return

    logger.info(f"Loaded {len(ads)} ads from {ADS_FILE}")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()

        print(f"\n[INFO] Opening target website: {TARGET_PORTAL_URL}")
        try:
            page.goto(TARGET_PORTAL_URL, wait_until="domcontentloaded")
        except Exception:
            pass

        print("\n" + "=" * 70)
        print("BROWSER SESSION READY")
        print("1. Log into the site if needed.")
        print("2. Click to the 'Post Ad' / 'Single Advert' form page.")
        print("3. Press ENTER in this terminal once you are on the form page.")
        print("=" * 70 + "\n")

        input(">>> Press ENTER when ready to start filling ads...")
        form_url = page.url

        for idx, car in enumerate(ads, start=1):
            print(f"\n" + "-" * 70)
            print(f"[CAR {idx}/{len(ads)}] Processing Listing ID: {car.get('source_id')} | Title: {car.get('title')}")
            print("-" * 70)

            # 1. Return to fresh Post Ad page if needed
            if page.url != form_url:
                page.goto(form_url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

            # 2. Select Category (Vehicles -> Cars -> Used cars in South Africa)
            cascader = DynamicCategoryCascader(page)
            if not cascader.select_categories():
                print(f"[WARN] Category selection step failed for item {car.get('source_id')}")

            page.wait_for_timeout(1000)

            # 3. Fill All Form Fields
            filler = RobustFormFiller(page)
            filler.fill_all_car_fields(car)

            # 4. Upload Up to 5 Images
            images = car.get("images", [])
            if images:
                filler.upload_images(images)

            print("\n" + "!" * 70)
            print(f"[CAR {idx}/{len(ads)}] Form filled completely!")
            print("Action Required: Check the form fields in the browser.")
            print("Click the 'Post Ad' button manually when satisfied.")
            print("!" * 70 + "\n")

            input(f">>> Press ENTER after you have posted Car {idx}/{len(ads)} to proceed to the next car...")

        print("\n[COMPLETE] All advertisements processed successfully!")
        try:
            context.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_batch()