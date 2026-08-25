import json
import logging
from pathlib import Path

from config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "ads_ready_for_form.json"
USED_FILE = OUTPUT_DIR / "used_cars.json"
OUTPUT_FILE = OUTPUT_DIR / "unique_ads.json"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def load_json(file_path, default):

    if not Path(file_path).exists():
        return default

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        logger.error(
            "Could not read %s: %s",
            file_path,
            error
        )

        return default


def save_json(file_path, data):

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def get_vehicle_id(ad):

    # Best option: source listing URL
    url = ad.get("source_url")

    if url:
        return str(url).strip().lower()

    # Second option: source/reference ID
    source_id = ad.get("source_id")

    if source_id:
        return (
            "reference:"
            + str(source_id).strip().lower()
        )

    # Last-resort fallback
    values = [
        ad.get("year", ""),
        ad.get("make", ""),
        ad.get("model", ""),
        ad.get("variant", ""),
        ad.get("mileage", ""),
    ]

    return "|".join(
        str(value).strip().lower()
        for value in values
    )


def main():

    logger.info("=" * 60)
    logger.info("DUPLICATE CHECK")
    logger.info("=" * 60)

    ads = load_json(
        INPUT_FILE,
        []
    )

    used_cars = load_json(
        USED_FILE,
        []
    )

    if not isinstance(ads, list):

        logger.error(
            "ads_ready_for_form.json must contain a list."
        )

        return

    if not isinstance(used_cars, list):

        used_cars = []

    # Convert previous IDs to a set for fast lookup
    used_ids = set()

    for item in used_cars:

        if isinstance(item, dict):

            vehicle_id = item.get(
                "vehicle_id"
            )

        else:

            vehicle_id = item

        if vehicle_id:
            used_ids.add(
                str(vehicle_id).strip().lower()
            )

    unique_ads = []

    duplicate_count = 0

    for ad in ads:

        vehicle_id = get_vehicle_id(ad)

        if vehicle_id in used_ids:

            duplicate_count += 1

            logger.warning(
                "DUPLICATE SKIPPED: %s",
                ad.get("source_url", "")
            )

            continue

        # Add to current run
        used_ids.add(vehicle_id)

        unique_ads.append(ad)

    # Save the unique ads for this run
    save_json(
        OUTPUT_FILE,
        unique_ads
    )

    # IMPORTANT:
    # We record them in the used-car database only after
    # they have passed this duplicate stage.
    #
    # The actual "posted successfully" status should be
    # recorded later by the posting controller.

    current_records = []

    for ad in unique_ads:

        current_records.append(
            {
                "vehicle_id": get_vehicle_id(ad),
                "source_url": ad.get(
                    "source_url",
                    ""
                ),
                "year": ad.get(
                    "year",
                    ""
                ),
                "make": ad.get(
                    "make",
                    ""
                ),
                "model": ad.get(
                    "model",
                    ""
                ),
                "variant": ad.get(
                    "variant",
                    ""
                )
            }
        )

    # Merge without duplicates
    existing_records = []

    for item in used_cars:

        if isinstance(item, dict):

            existing_records.append(item)

    existing_ids = {
        item.get("vehicle_id")
        for item in existing_records
        if item.get("vehicle_id")
    }

    for record in current_records:

        if record["vehicle_id"] not in existing_ids:

            existing_records.append(record)

    save_json(
        USED_FILE,
        existing_records
    )

    logger.info("=" * 60)
    logger.info(
        "Ads received: %s",
        len(ads)
    )
    logger.info(
        "Unique ads: %s",
        len(unique_ads)
    )
    logger.info(
        "Duplicates skipped: %s",
        duplicate_count
    )
    logger.info(
        "Unique output: %s",
        OUTPUT_FILE
    )
    logger.info(
        "Used-car database: %s",
        USED_FILE
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()