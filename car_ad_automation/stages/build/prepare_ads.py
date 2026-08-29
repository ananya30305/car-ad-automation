import json
import logging
from pathlib import Path

from car_ad_automation.core.config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "car_details.json"
OUTPUT_FILE = OUTPUT_DIR / "ready_ads.json"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def build_description(car):
    """
    Creates a factual description only from information
    already extracted from the source listing.
    """

    year = clean(car.get("year"))
    make = clean(car.get("make"))
    model = clean(car.get("model"))
    variant = clean(car.get("variant"))
    mileage = clean(car.get("mileage"))
    transmission = clean(car.get("transmission"))
    fuel = clean(car.get("fuel"))
    drive_type = clean(car.get("drive_type"))
    colour = clean(car.get("colour"))
    price = clean(car.get("price"))

    title_parts = []

    if year:
        title_parts.append(year)

    if make:
        title_parts.append(make)

    if model:
        title_parts.append(model)

    if variant:
        title_parts.append(variant)

    title = " ".join(title_parts)

    sentences = []

    if title:
        sentences.append(title)

    details = []

    if mileage:
        details.append(mileage)

    if transmission:
        details.append(transmission)

    if fuel:
        details.append(fuel)

    if drive_type:
        details.append(drive_type)

    if colour:
        details.append(colour)

    if details:
        sentences.append(
            "Vehicle details: " + ", ".join(details) + "."
        )

    if price:
        sentences.append(
            f"Listed price: {price}."
        )

    return " ".join(sentences)


def prepare_car(car, index):
    """
    Convert extracted data into the structure expected
    by the form-filling stage.
    """

    year = clean(car.get("year"))
    make = clean(car.get("make"))
    model = clean(car.get("model"))
    variant = clean(car.get("variant"))

    mileage = clean(car.get("mileage"))
    transmission = clean(car.get("transmission"))
    fuel = clean(car.get("fuel"))
    drive_type = clean(car.get("drive_type"))
    colour = clean(car.get("colour"))
    condition = clean(car.get("condition"))
    price = clean(car.get("price"))

    description = clean(car.get("description"))

    if not description:
        description = build_description(car)

    features = car.get("features", [])

    if not isinstance(features, list):
        features = []

    highlights = car.get("highlights", [])

    if not isinstance(highlights, list):
        highlights = []

    return {
        "id": index,

        "source_url": clean(
            car.get("source_url")
        ),

        "title": clean(
            car.get("title")
        ),

        "year": year,

        "make": make,

        "model": model,

        "variant": variant,

        "mileage": mileage,

        "transmission": transmission,

        "fuel": fuel,

        "drive_type": drive_type,

        "colour": colour,

        "condition": condition,

        "price": price,

        "description": description,

        "highlights": highlights,

        "features": features,

        "status": "READY",
    }


def main():

    logger.info(
        "Loading extracted vehicle data..."
    )

    if not INPUT_FILE.exists():

        logger.error(
            "File not found: %s",
            INPUT_FILE
        )

        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        cars = json.load(file)

    if not isinstance(cars, list):

        logger.error(
            "car_details.json must contain a list."
        )

        return

    ready_ads = []

    for index, car in enumerate(
        cars,
        start=1
    ):

        prepared = prepare_car(
            car,
            index
        )

        ready_ads.append(
            prepared
        )

        logger.info(
            "[%d/%d] %s %s %s",
            index,
            len(cars),
            prepared["year"],
            prepared["make"],
            prepared["model"]
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            ready_ads,
            file,
            indent=4,
            ensure_ascii=False
        )

    logger.info(
        "========================================"
    )

    logger.info(
        "Prepared %d advertisements.",
        len(ready_ads)
    )

    logger.info(
        "Output: %s",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()