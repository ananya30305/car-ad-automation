import json
import logging
from pathlib import Path

from car_ad_automation.core.config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "ads_with_images.json"
OUTPUT_FILE = OUTPUT_DIR / "preflight_ready.json"
REJECTED_FILE = OUTPUT_DIR / "preflight_rejected.json"

REQUIRED_FIELDS = [
    "source_url",
    "year",
    "make",
    "model",
    "mileage",
    "transmission",
    "fuel",
    "drive_type",
    "condition",
    "price",
]

MIN_HIGHLIGHTS = 1
MIN_FEATURES = 3
MAX_MISSING_CATEGORIES = 3
REQUIRED_IMAGES = 5


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

    return str(value).strip()


def validate_car(car):

    errors = []

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    for field in REQUIRED_FIELDS:

        value = car.get(field)

        if value is None:
            errors.append(
                f"Missing field: {field}"
            )
            continue

        if isinstance(value, str):
            if not value.strip():
                errors.append(
                    f"Missing field: {field}"
                )

    # --------------------------------------------------------
    # Missing categories
    # --------------------------------------------------------

    missing_categories = car.get(
        "missing_categories",
        []
    )

    if not isinstance(
        missing_categories,
        list
    ):
        missing_categories = []

    if len(missing_categories) > MAX_MISSING_CATEGORIES:

        errors.append(
            "More than 3 categories are missing"
        )

    # --------------------------------------------------------
    # Highlights
    # --------------------------------------------------------

    highlights = car.get(
        "highlights",
        []
    )

    if not isinstance(
        highlights,
        list
    ):
        highlights = []

    highlights = [
        clean(item)
        for item in highlights
        if clean(item)
    ]

    if len(highlights) < MIN_HIGHLIGHTS:

        errors.append(
            "Fewer than 1 highlight"
        )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    features = car.get(
        "features",
        []
    )

    if not isinstance(
        features,
        list
    ):
        features = []

    features = [
        clean(item)
        for item in features
        if clean(item)
    ]

    if len(features) < MIN_FEATURES:

        errors.append(
            "Fewer than 3 features"
        )

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    images = car.get(
        "images",
        []
    )

    if not isinstance(
        images,
        list
    ):
        images = []

    real_images = []

    for image in images:

        image = clean(image)

        if (
            image.startswith("http://")
            or image.startswith("https://")
        ):

            if "placeholder" not in image.lower():

                real_images.append(image)

    if len(real_images) < REQUIRED_IMAGES:

        errors.append(
            f"Fewer than {REQUIRED_IMAGES} usable images"
        )

    # --------------------------------------------------------
    # Source URL
    # --------------------------------------------------------

    source_url = clean(
        car.get("source_url")
    )

    if not source_url:

        errors.append(
            "No source URL"
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = dict(car)

    result["highlights"] = highlights
    result["features"] = features
    result["images"] = real_images[:REQUIRED_IMAGES]
    result["preflight_errors"] = errors
    result["preflight_ready"] = (
        len(errors) == 0
    )

    return result


def main():

    logger.info("=" * 70)
    logger.info("PREFLIGHT CHECK")
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
            "Input must contain a list."
        )

        return

    ready = []
    rejected = []

    # Used again as an additional duplicate safety check.
    seen_urls = set()

    for number, car in enumerate(
        cars,
        start=1
    ):

        if not isinstance(
            car,
            dict
        ):
            continue

        result = validate_car(
            car
        )

        source_url = clean(
            result.get(
                "source_url"
            )
        )

        # ----------------------------------------------------
        # Duplicate protection
        # ----------------------------------------------------

        if source_url:

            if source_url in seen_urls:

                result["preflight_errors"].append(
                    "Duplicate source URL"
                )

                result["preflight_ready"] = False

            else:

                seen_urls.add(
                    source_url
                )

        title = clean(
            result.get(
                "title",
                ""
            )
        )

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        if result["preflight_ready"]:

            ready.append(
                result
            )

            logger.info(
                "[READY] %d | %s",
                number,
                title
            )

        else:

            rejected.append(
                result
            )

            logger.warning(
                "[REJECTED] %d | %s",
                number,
                title
            )

            for error in result[
                "preflight_errors"
            ]:

                logger.warning(
                    "    %s",
                    error
                )

    save_json(
        OUTPUT_FILE,
        ready
    )

    save_json(
        REJECTED_FILE,
        rejected
    )

    logger.info("=" * 70)
    logger.info("PREFLIGHT COMPLETE")
    logger.info(
        "Input       : %d",
        len(cars)
    )
    logger.info(
        "Ready       : %d",
        len(ready)
    )
    logger.info(
        "Rejected    : %d",
        len(rejected)
    )
    logger.info(
        "Ready file  : %s",
        OUTPUT_FILE
    )
    logger.info(
        "Reject file : %s",
        REJECTED_FILE
    )
    logger.info("=" * 70)


if __name__ == "__main__":
    main()