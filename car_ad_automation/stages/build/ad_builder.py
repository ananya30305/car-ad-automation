"""Ad Builder - Formats payload details and verifies image file paths."""

import json
import logging
from pathlib import Path

from car_ad_automation.core.config import DATA_DIR, OUTPUT_DIR

INPUT_FILE = OUTPUT_DIR / "car_details.json"
OUTPUT_FILE = OUTPUT_DIR / "ads_ready_for_form.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def build_payload(car: dict) -> dict:
    source_id = car.get("source_id", "")
    images = car.get("images", [])
    
    valid_images = []
    for img_p in images:
        p = Path(img_p)
        if p.exists():
            valid_images.append(str(p.resolve()))

    if not valid_images and source_id:
        local_dir = DATA_DIR / "images" / source_id
        if local_dir.exists():
            valid_images = [str(f.resolve()) for f in sorted(local_dir.glob("*.jpg"))]

    car_payload = dict(car)
    car_payload["images"] = valid_images[:5]
    return car_payload


def main():
    if not INPUT_FILE.exists():
        logger.error("Input file not found: %s", INPUT_FILE)
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        cars = json.load(f)

    ads = [build_payload(c) for c in cars]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ads, f, indent=4, ensure_ascii=False)

    logger.info("Prepared %d advertisements payload.", len(ads))


if __name__ == "__main__":
    main()