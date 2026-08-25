import json
import logging
from pathlib import Path


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "output" / "cars.json"
OUTPUT_FILE = BASE_DIR / "output" / "car_details.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def clean(value):
    """
    Return a usable value.
    If the source doesn't contain a value, use '.'.
    """
    if value is None:
        return "."

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return "."

    return value


def clean_list(value):
    """
    Clean feature/highlight lists.
    """
    if not value:
        return []

    if not isinstance(value, list):
        return [str(value).strip()]

    result = []

    for item in value:
        item = str(item).strip()

        if item:
            result.append(item)

    return result


def price_number(price):
    """
    Convert:
        R 449 900
    into:
        449900

    If price is unavailable, return '.'.
    """
    price = clean(price)

    if price == ".":
        return "."

    digits = "".join(ch for ch in str(price) if ch.isdigit())

    return digits if digits else "."


# ---------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------

def extract_car(car):

    title = clean(car.get("title"))

    result = {
        # Source
        "source_url": clean(car.get("source_url")),

        # Main advert information
        "title": title,
        "title_description": clean(car.get("description")),

        # Vehicle information
        "condition": clean(car.get("condition")),
        "year": clean(car.get("year")),
        "mileage": clean(car.get("mileage")),
        "transmission": clean(car.get("transmission")),
        "fuel": clean(car.get("fuel")),
        "drive_type": clean(car.get("drive_type")),
        "colour": clean(car.get("colour")),

        # Required JomClassifieds fields
        "seats": ".",
        "pricing_summary": clean(car.get("price")),

        # Dealer information
        "dealer_name": ".",
        "dealer_address": ".",
        "dealer_rating": ".",
        "contact_number": ".",

        # Features / highlights
        "features": clean_list(car.get("features")),
        "highlights": clean_list(car.get("highlights")),

        # Description
        "description": clean(car.get("description")),

        # Price
        "price": price_number(car.get("price")),
        "currency": "R (Rand)",

        # Final address
        "address": "."
    }

    return result


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    logger.info("=" * 70)
    logger.info("CAR DATA EXTRACTION")
    logger.info("=" * 70)

    if not INPUT_FILE.exists():
        logger.error("Input file not found:")
        logger.error(str(INPUT_FILE))
        return

    logger.info("Loading source car list...")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        cars = json.load(f)

    logger.info("Found %d source records.", len(cars))

    extracted = []

    for index, car in enumerate(cars, start=1):

        result = extract_car(car)

        extracted.append(result)

        logger.info(
            "[%d/%d] %s | %s | %s | %s",
            index,
            len(cars),
            result["year"],
            result["title"],
            result["transmission"],
            result["mileage"]
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            extracted,
            f,
            indent=4,
            ensure_ascii=False
        )

    logger.info("Saved %d extracted records.", len(extracted))
    logger.info("Output: %s", OUTPUT_FILE)

    logger.info("=" * 70)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()