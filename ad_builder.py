import json
import logging
from pathlib import Path

from config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "validated_cars.json"
OUTPUT_FILE = OUTPUT_DIR / "ads_ready_for_form.json"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def load_json(file_path):

    if not Path(file_path).exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_json(file_path, data):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

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


def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def prepare_missing_values(ad):

    """
    The advertisement rules allow '.' for a genuinely
    missing category.

    We ONLY use '.' for fields that are actually missing.

    We do NOT replace missing highlights/features with '.'
    because those have separate minimum requirements.
    """

    result = dict(ad)

    missing_fields = result.get(
        "validation",
        {}
    ).get(
        "missing_fields",
        []
    )

    if not isinstance(
        missing_fields,
        list
    ):

        missing_fields = []

    for field in missing_fields:

        if field in result:

            if not clean(
                result[field]
            ):

                result[field] = "."

        else:

            result[field] = "."

    return result


def build_form_record(ad, number):

    ad = prepare_missing_values(
        ad
    )

    highlights = ad.get(
        "highlights",
        []
    )

    features = ad.get(
        "features",
        []
    )

    if not isinstance(
        highlights,
        list
    ):

        highlights = []

    if not isinstance(
        features,
        list
    ):

        features = []

    record = {

        "ad_number": number,

        "source_id": ad.get(
            "source_id",
            ""
        ),

        "source_url": ad.get(
            "source_url",
            ""
        ),

        "year": clean(
            ad.get("year")
        ),

        "make": clean(
            ad.get("make")
        ),

        "model": clean(
            ad.get("model")
        ),

        "variant": clean(
            ad.get("variant")
        ),

        "mileage": clean(
            ad.get("mileage")
        ),

        "transmission": clean(
            ad.get("transmission")
        ),

        "fuel": clean(
            ad.get("fuel")
        ),

        "drive_type": clean(
            ad.get("drive_type")
        ),

        "condition": clean(
            ad.get("condition")
        ),

        "price": clean(
            ad.get("price")
        ),

        "highlights": highlights,

        "features": features,

        "images": ad.get(
            "images",
            []
        ),

        "validation": ad.get(
            "validation",
            {}
        ),
    }

    return record


def main():

    logger.info("=" * 70)
    logger.info("ADVERTISEMENT BUILDER")
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
            "validated_cars.json must contain a list."
        )

        return

    ads = []

    for number, car in enumerate(
        cars,
        start=1
    ):

        record = build_form_record(
            car,
            number
        )

        ads.append(
            record
        )

        logger.info(
            "[%d] Prepared: %s %s %s",
            number,
            record["year"],
            record["make"],
            record["model"]
        )

    save_json(
        OUTPUT_FILE,
        ads
    )

    logger.info("=" * 70)

    logger.info(
        "Prepared advertisements: %d",
        len(ads)
    )

    logger.info(
        "Output: %s",
        OUTPUT_FILE
    )

    logger.info("=" * 70)


if __name__ == "__main__":
    main()