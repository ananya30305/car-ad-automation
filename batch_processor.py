"""Batch Processor - Runs RobustFormFiller directly for category selection and field population."""

import json
import logging
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from form_filler import RobustFormFiller
from config import OUTPUT_DIR

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
PROFILE_DIR = BASE_DIR / "browser_profile"

ADS_FILE = OUTPUT_DIR / "ads_ready_for_form.json"
CARS_JSON = OUTPUT_DIR / "cars.json"
INVENTORY_JSON = DATA_DIR / "inventory.json"
POSTED_LOG_FILE = OUTPUT_DIR / "carlist.txt"

TARGET_PORTAL_URL = "https://august2026karnataka.dicewebfreelancers.com/index.php/my-ads"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def log_posted_car(car: dict):
    """Appends only the car title to carlist.txt file."""
    try:
        title = car.get("title") or "Unknown Title"
        
        with open(POSTED_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{title}\n")
            
        print(f"[LOGGED] Added '{title}' to carlist.txt")
    except Exception as e:
        logger.warning(f"Failed to log posted car to carlist.txt: {e}")


def remove_processed_car(source_id: str):
    """Removes a processed car from JSON queue files and deletes its local image directory."""
    if not source_id or source_id == ".":
        return

    # 1. Update JSON files (Remove posted car)
    json_targets = [ADS_FILE, CARS_JSON, INVENTORY_JSON]
    for json_file in json_targets:
        if json_file.exists():
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    updated_data = [
                        item for item in data
                        if str(item.get("source_id") or item.get("id")) != str(source_id)
                    ]
                    json_file.write_text(json.dumps(updated_data, indent=4, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to update {json_file.name}: {e}")

    # 2. Delete local image folder for this car
    car_img_dir = IMAGES_DIR / str(source_id)
    if car_img_dir.exists():
        try:
            shutil.rmtree(car_img_dir)
            logger.info(f"Deleted local image directory for car ID: {source_id}")
        except Exception as e:
            logger.warning(f"Failed to delete image directory {car_img_dir}: {e}")


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
            args=["--start-maximized"],
            no_viewport=True
        )
        page = context.pages[0] if context.pages else context.new_page()

        print(f"\n[INFO] Opening target website: {TARGET_PORTAL_URL}")
        try:
            page.goto(TARGET_PORTAL_URL, wait_until="domcontentloaded")
        except Exception:
            pass

        idx = 1
        while True:
            # Re-read ads queue file dynamically to support resume capability
            if ADS_FILE.exists():
                ads = json.loads(ADS_FILE.read_text(encoding="utf-8"))
            else:
                ads = []

            if not ads:
                print("\n[COMPLETE] All advertisements processed successfully!")
                break

            car = ads[0]
            source_id = str(car.get("source_id") or car.get("id"))
            source_link = car.get("Source Link") or car.get("source_url") or "."
            total_remaining = len(ads)

            print("\n" + "=" * 70)
            print(f"[CAR {idx} | REMAINING IN QUEUE: {total_remaining}] READY TO FILL CAR RECORD")
            print(f"Title: {car.get('title')} | ID: {source_id}")
            print(f"Source Link: {source_link}")
            print("1. Open/Navigate to the 'Post Ad' form page in your browser.")
            print("2. Ensure you are on the blank Post Ad page.")
            print("3. Press ENTER in this terminal to start auto-filling.")
            print("=" * 70 + "\n")

            input(f">>> Press ENTER when ready to start filling Car ID {source_id}...")

            # fill_all_car_fields handles categories, inputs, textareas, dropdowns, description, AND image upload
            filler = RobustFormFiller(page)
            filler.fill_all_car_fields(car)

            print("\n" + "!" * 70)
            print(f"[CAR {idx}] Form filled completely!")
            print("Action Required: Check the form fields, check Privacy Policy, and submit or cancel the ad.")
            print("!" * 70 + "\n")

            # --- PROMPT POST / CANCEL DECISION ---
            try:
                user_choice = input(f">>> Did you post this ad or cancel it? (y = Posted, n = Canceled): ").strip().lower()
                
                if user_choice in ["y", "yes"]:
                    log_posted_car(car)
                else:
                    print(f"[SKIPPED LOG] Ad for Car ID {source_id} was marked as Canceled/Not Posted.")
            except KeyboardInterrupt:
                print(f"\n[INTERRUPTED] Process stopped by user. Queue preserved.")
                break

            # Remove data & images once decision is made so queue stays clean
            remove_processed_car(source_id)
            print(f"[SUCCESS] Cleaned up Car ID {source_id} from queue.")

            idx += 1

        try:
            context.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_batch()