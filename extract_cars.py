"""Extracts and formats scraped car data into the exact schema expected by form_filler.py."""

import json
import logging
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "inventory.json"
OUTPUT_FILE = BASE_DIR / "output" / "ads_ready_for_form.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def clean(val, fallback=".") -> str:
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s and s != "." else fallback


def extract_car(car: dict) -> dict:
    source_id = clean(car.get("id") or car.get("source_id"))
    title = clean(car.get("title"), fallback="Used Car")
    variant = clean(car.get("title description") or car.get("variant"), fallback=title)
    
    # Raw numeric price
    raw_price = str(car.get("price", "0")).replace("R", "").replace(" ", "").strip()
    price_val = raw_price if raw_price.isdigit() and raw_price != "0" else "0"

    phone = clean(car.get("contact_number") or car.get("contact_phone"))
    dealer = clean(car.get("dealer_name"))
    address = clean(car.get("dealer_address") or car.get("address"))
    source_url = clean(car.get("Source Link") or car.get("source_url"))
    rating = clean(car.get("Dealer average rating") or car.get("dealer_rating"), fallback="4.0 (322 reviews)")
    
    # Ensure mileage has "km"
    mileage_raw = clean(car.get("Kilometers driven") or car.get("mileage"))
    if mileage_raw != "." and "km" not in mileage_raw.lower():
        mileage_str = f"{mileage_raw} km"
    else:
        mileage_str = mileage_raw

    year = clean(car.get("year"))
    trans = clean(car.get("transmission"), fallback="Automatic")
    fuel = clean(car.get("fuel"), fallback="Petrol")
    drive = clean(car.get("4x2 / 4x4") or car.get("drive_type"), fallback="4x2")
    colour = clean(car.get(" body colour") or car.get("colour"))
    
    # Features formatting
    feats = car.get("features", [])
    if isinstance(feats, list) and feats:
        features_txt = "\n".join([str(f).strip() for f in feats if str(f).strip()])
    else:
        features_txt = clean(feats)

    # Highlights formatting
    highs = car.get("vehicle highlights") or car.get("highlights", [])
    if isinstance(highs, list) and highs:
        highlights_txt = "\n".join([str(h).strip() for h in highs if str(h).strip()])
    else:
        highlights_txt = clean(highs)

    desc = clean(car.get("description"), fallback=title)
    
    # Dynamic Pricing Summary
    ps = car.get("price summary") or car.get("pricing_summary")
    if ps and ps != ".":
        pricing_summary = str(ps).strip()
    else:
        pricing_summary = f"Pricing Summary R {price_val} Est. R 5 347 p/m"

    # Verify isolated local images
    images = car.get("images", [])
    valid_images = []
    for img_p in images:
        p = Path(img_p)
        if p.exists():
            valid_images.append(str(p.resolve()))

    if not valid_images and source_id != ".":
        local_dir = BASE_DIR / "data" / "images" / source_id
        if local_dir.exists():
            valid_images = [str(f.resolve()) for f in sorted(local_dir.glob("*.jpg")) + sorted(local_dir.glob("*.png"))]

    return {
        "source_id": source_id,
        "Source Link": source_url,
        "source_url": source_url,
        
        "title": title,
        "title description": variant,
        "variant": variant,
        
        "condition": "Used",
        "year": year,
        "Kilometers driven": mileage_str,
        "mileage": mileage_str,
        "transmission": trans,
        "fuel": fuel,
        "4x2 / 4x4": drive,
        "drive_type": drive,
        "body colour": colour,
        "colour": colour,
        "seats": clean(car.get("seats")),
        
        "price summary": pricing_summary,
        "pricing_summary": pricing_summary,
        "dealer_name": dealer,
        "dealer_address": address,
        "address": address,
        "Dealer average rating": rating,
        "dealer_rating": rating,
        "contact_number": phone,
        "contact_phone": phone,
        
        "features": features_txt,
        "vehicle highlights": highlights_txt,
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