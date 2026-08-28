"""Formats scraped cars into the exact JSON schema required by batch_processor.py."""

import json
import logging
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
    
    raw_price = str(car.get("price", "0")).replace("R", "").replace(" ", "").strip()
    price_val = raw_price if raw_price.isdigit() and raw_price != "0" else "0"

    phone = clean(car.get("contact_number") or car.get("contact_phone"))
    dealer = clean(car.get("dealer_name"))
    address = clean(car.get("dealer_address") or car.get("address"))
    source_url = clean(car.get("Source Link") or car.get("source_url"))
    rating = clean(car.get("Dealer average rating") or car.get("dealer_rating"), fallback="4.0 (322 reviews)")

    mileage_raw = clean(car.get("Kilometers driven") or car.get("mileage"))
    mileage_str = f"{mileage_raw} km" if mileage_raw != "." and "km" not in mileage_raw.lower() else mileage_raw

    year = clean(car.get("year"))
    trans = clean(car.get("transmission"), fallback="Automatic")
    fuel = clean(car.get("fuel"), fallback="Petrol")
    drive = clean(car.get("4x2 / 4x4") or car.get("drive_type"), fallback="4x2")
    colour = clean(car.get("body colour") or car.get("colour"))
    cond = clean(car.get("condition"), fallback="Used")

    feats = car.get("features", [])
    features_txt = "\n".join([str(f).strip() for f in feats if str(f).strip()]) if isinstance(feats, list) else clean(feats)

    highs = car.get("vehicle highlights") or car.get("highlights", [])
    highlights_txt = "\n".join([str(h).strip() for h in highs if str(h).strip()]) if isinstance(highs, list) else clean(highs)

    desc = clean(car.get("description"), fallback=title)
    ps = car.get("price summary") or car.get("pricing_summary")
    pricing_summary = str(ps).strip() if ps and ps != "." else f"Pricing Summary R {price_val} Est. R 5 347 p/m"

    images = car.get("images", [])
    valid_images = [str(Path(p).resolve()) for p in images if Path(p).exists()]

    return {
        "source_id": source_id,
        "Source Link": source_url,
        "source_url": source_url,
        "title": title,
        "title description": variant,
        "variant": variant,
        "condition": cond,
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