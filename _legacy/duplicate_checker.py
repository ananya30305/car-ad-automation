import json
import logging
from pathlib import Path

from config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "ads_with_images.json"
OUTPUT_FILE = OUTPUT_DIR / "unique_ads.json"
DUPLICATES_FILE = OUTPUT_DIR / "duplicates.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def load_json(path):

    if not Path(path).exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_json(path, data):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def clean(value):

    if value is None:
        return ""

    return str(value).strip().lower()


def get_unique_key(car):

    """
    Prefer the Cars.co.za listing ID.

    Example:
    https://www.cars.co.za/for-sale/used/...
    /11193474/

    If an ID isn't available, use the source URL.
    """

    source_id = clean(
        car.get("source_id")
    )

    if source_id:
        return f"id:{source_id}"

    source_url = clean(
        car.get("source_url")
    )

    if source_url:
        return f"url:{source_url}"

    # Last-resort identity based on vehicle information.
    return "|".join(
        [
            clean(car.get("year")),
            clean(car.get("make")),
            clean(car.get("model")),
            clean(car.get("variant")),
            clean(car.get("mileage")),
            clean(car.get("price")),
        ]
    )


def main():

    logger.info("=" * 70)
    logger.info("DUPLICATE CHECKER")
    logger.info("=" * 70)

    try:
        cars = load_json(
            INPUT_FILE
        )

    except Exception as error:

        logger.error(
            "%s",
            error
        )

        return

    if not isinstance(
        cars,
        list
    ):

        logger.error(
            "Input file must contain a list."
        )

        return

    unique_cars = []
    duplicate_cars = []

    seen = set()

    for number, car in enumerate(
        cars,
        start=1
    ):

        if not isinstance(
            car,
            dict
        ):
            continue

        key = get_unique_key(
            car
        )

        if not key.strip():

            logger.warning(
                "[%d] Could not determine identity.",
                number
            )

            duplicate_cars.append(
                car
            )

            continue

        if key in seen:

            duplicate_cars.append(
                car
            )

            logger.warning(
                "[DUPLICATE] %s",
                key
            )

            continue

        seen.add(
            key
        )

        unique_cars.append(
            car
        )

        logger.info(
            "[UNIQUE] %s %s %s",
            car.get("year", ""),
            car.get("make", ""),
            car.get("model", "")
        )

    save_json(
        OUTPUT_FILE,
        unique_cars
    )

    save_json(
        DUPLICATES_FILE,
        duplicate_cars
    )

    logger.info("=" * 70)

    logger.info(
        "Input cars     : %d",
        len(cars)
    )

    logger.info(
        "Unique cars    : %d",
        len(unique_cars)
    )

    logger.info(
        "Duplicates     : %d",
        len(duplicate_cars)
    )

    logger.info(
        "Unique output  : %s",
        OUTPUT_FILE
    )

    logger.info(
        "Duplicate file : %s",
        DUPLICATES_FILE
    )

    logger.info("=" * 70)


if __name__ == "__main__":
    main()