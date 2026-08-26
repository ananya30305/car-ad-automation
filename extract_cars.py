"""Extracts and formats scraped car data directly into the form's expected payload schema."""

import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "output" / "cars.json"
OUTPUT_FILE = BASE_DIR / "output" / "car_details.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def clean(val, fallback=".") -> str:
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s and s != "." else fallback


def extract_car(car: dict) -> dict:
    source_id = clean(car.get("source_id"))
    title = clean(car.get("title"), fallback="Used Car")
    variant = clean(car.get("variant"), fallback=title)
    
    price_val = clean(car.get("price"), fallback="0").replace("R", "").replace(" ", "").strip()
    if not price_val.isdigit():
        price_val = "0"

    phone = clean(car.get("contact_phone") or car.get("contact_number"))
    dealer = clean(car.get("dealer_name"))
    address = clean(car.get("dealer_address"))
    source_url = clean(car.get("source_url"))
    rating = clean(car.get("dealer_rating"), fallback="4.5")
    
    mileage = clean(car.get("mileage")).replace("km", "").strip()
    year = clean(car.get("year"))
    trans = clean(car.get("transmission"), fallback="Automatic")
    fuel = clean(car.get("fuel"), fallback="Petrol")
    drive = clean(car.get("drive_type"), fallback="4x2")
    colour = clean(car.get("colour"))
    
    features = car.get("features", [])
    features_str = "\n".join(features) if isinstance(features, list) and features else "."
    
    highlights = car.get("highlights", [])
    highlights_str = "\n".join(highlights) if isinstance(highlights, list) and highlights else "."
    
    desc = clean(car.get("description"), fallback=title)

    # Verify local image paths on disk
    images = car.get("images", [])
    valid_images = []
    for img_p in images:
        p = Path(img_p)
        if p.exists():
            valid_images.append(str(p.resolve()))

    if not valid_images and source_id != ".":
        local_dir = BASE_DIR / "data" / "images" / source_id
        if local_dir.exists():
            valid_images = [str(f.resolve()) for f in sorted(local_dir.glob("*.jpg"))]

    return {
        "source_id": source_id,
        "source_url": source_url,
        "source_link": source_url,
        
        "title": title,
        "name": title,
        "title_description": variant,
        "variant": variant,
        "vehicle": variant,
        
        "condition": "Used",
        "year": year,
        "mileage": mileage,
        "kilometer": mileage,
        "kilometers_driven": mileage,
        "transmission": trans,
        "fuel": fuel,
        "engine": fuel,
        "drive_type": drive,
        "colour": colour,
        "color": colour,
        "interior_colour": ".",
        "seats": clean(car.get("seats")),
        "seating": clean(car.get("seats")),
        
        "pricing_summary": f"Pricing Summary R {price_val}",
        "dealer_name": dealer,
        "dealer_address": address,
        "address": address,
        "dealer_rating": rating,
        "rating": rating,
        "contact_number": phone,
        "contact_phone": phone,
        "phone": phone,
        
        "features": features_str,
        "comfort": features_str,
        "highlights": highlights_str,
        "exterior": highlights_str,
        "description": desc,
        
        "price": price_val,
        "currency": "R (Rand)",
        "tag": "Sale",
        "location": "South Africa",
        "images": valid_images[:5]
    }


def main():
    if not INPUT_FILE.exists():
        logger.error("Input file not found: %s", INPUT_FILE)
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        cars = json.load(f)

    extracted = [extract_car(c) for c in cars]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=4, ensure_ascii=False)

    logger.info("Successfully exported %d structured car records to %s", len(extracted), OUTPUT_FILE)


if __name__ == "__main__":
    main()