import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "validated_cars.json"
OUTPUT_FILE = OUTPUT_DIR / "ads_with_images.json"
REJECTED_FILE = OUTPUT_DIR / "image_rejected_cars.json"

REQUIRED_IMAGES = 5


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# LOAD / SAVE
# ============================================================

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


# ============================================================
# TEXT CLEANING
# ============================================================

def clean(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# CHECK WHETHER IMAGE IS A PLACEHOLDER
# ============================================================

def is_placeholder(url):

    if not url:
        return True

    lowered = url.lower()

    placeholder_words = [
        "placeholder",
        "no-image",
        "no_image",
        "default-image",
        "default_image"
    ]

    for word in placeholder_words:

        if word in lowered:
            return True

    return False


# ============================================================
# CHECK IMAGE URL
# ============================================================

def is_valid_image_url(url):

    if not url:
        return False

    url = clean(url)

    if not url.startswith(
        ("http://", "https://")
    ):
        return False

    if is_placeholder(url):
        return False

    parsed = urlparse(url)

    if not parsed.netloc:
        return False

    return True


# ============================================================
# GET IMAGE LIST
# ============================================================

def get_image_list(car):

    possible_keys = [
        "images",
        "image_urls",
        "photos",
        "photo_urls",
        "gallery"
    ]

    images = []

    for key in possible_keys:

        value = car.get(key)

        if isinstance(value, list):

            images.extend(value)

        elif isinstance(value, str):

            if value.strip():
                images.append(value)

    # --------------------------------------------------------
    # Remove duplicates while preserving order
    # --------------------------------------------------------

    unique_images = []

    seen = set()

    for image in images:

        if isinstance(image, dict):

            image = (
                image.get("url")
                or image.get("src")
                or image.get("image_url")
                or ""
            )

        image = clean(image)

        if not is_valid_image_url(image):
            continue

        if image in seen:
            continue

        seen.add(image)

        unique_images.append(image)

    return unique_images


# ============================================================
# SELECT FIRST FIVE REAL IMAGES
# ============================================================

def select_images(car):

    images = get_image_list(car)

    selected = images[:REQUIRED_IMAGES]

    return selected


# ============================================================
# PROCESS ONE CAR
# ============================================================

def process_car(car):

    result = dict(car)

    selected_images = select_images(
        car
    )

    result["images"] = selected_images

    result["image_count"] = len(
        selected_images
    )

    if len(selected_images) >= REQUIRED_IMAGES:

        result["images_valid"] = True
        result["image_error"] = ""

        return result, True

    result["images_valid"] = False

    result["image_error"] = (
        f"Only {len(selected_images)} "
        f"usable images found; "
        f"{REQUIRED_IMAGES} required."
    )

    return result, False


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info("=" * 70)
    logger.info("IMAGE SELECTION STARTED")
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

    logger.info(
        "Loaded %d validated cars.",
        len(cars)
    )

    valid_ads = []
    rejected_cars = []

    for index, car in enumerate(
        cars,
        start=1
    ):

        result, valid = process_car(
            car
        )

        title = clean(
            car.get(
                "title",
                ""
            )
        )

        if valid:

            valid_ads.append(
                result
            )

            logger.info(
                "[IMAGE OK] %d/%d | %s | %d images",
                index,
                len(cars),
                title,
                result["image_count"]
            )

        else:

            rejected_cars.append(
                result
            )

            logger.warning(
                "[IMAGE REJECTED] %d/%d | %s | %s",
                index,
                len(cars),
                title,
                result["image_error"]
            )

    save_json(
        OUTPUT_FILE,
        valid_ads
    )

    save_json(
        REJECTED_FILE,
        rejected_cars
    )

    logger.info("=" * 70)

    logger.info(
        "IMAGE SELECTION COMPLETE"
    )

    logger.info(
        "Input cars       : %d",
        len(cars)
    )

    logger.info(
        "Ads with 5 images: %d",
        len(valid_ads)
    )

    logger.info(
        "Rejected         : %d",
        len(rejected_cars)
    )

    logger.info(
        "Output           : %s",
        OUTPUT_FILE
    )

    logger.info(
        "Rejected output  : %s",
        REJECTED_FILE
    )

    logger.info("=" * 70)


if __name__ == "__main__":
    main()