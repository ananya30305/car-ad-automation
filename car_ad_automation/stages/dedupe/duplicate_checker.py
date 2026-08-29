"""
Duplicate detection for vehicle advertisements.

Responsibilities:
- Load advertisements from ads_with_images.json
- Detect duplicates using strong identifiers first
- Fall back to source URL
- Fall back to normalized vehicle attributes
- Preserve the first occurrence
- Store duplicate records separately
- Produce a useful duplicate-detection report
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from car_ad_automation.core.config import OUTPUT_DIR


# ================================================================
# FILE CONFIGURATION
# ================================================================

INPUT_FILE = OUTPUT_DIR / "ads_with_images.json"
OUTPUT_FILE = OUTPUT_DIR / "unique_ads.json"
DUPLICATES_FILE = OUTPUT_DIR / "duplicates.json"
REPORT_FILE = OUTPUT_DIR / "duplicate_report.json"


# ================================================================
# LOGGING
# ================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ================================================================
# JSON HELPERS
# ================================================================

def load_json(path: Path) -> Any:
    """
    Load JSON from disk.

    Args:
        path:
            JSON file path.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError:
            If file does not exist.

        json.JSONDecodeError:
            If JSON is invalid.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(
    path: Path,
    data: Any,
) -> None:
    """
    Save data as formatted JSON.
    """

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )


# ================================================================
# VALUE NORMALIZATION
# ================================================================

def clean(value: Any) -> str:
    """
    Normalize a value for comparison.

    Examples:
        " Toyota " -> "toyota"
        None -> ""
    """

    if value is None:
        return ""

    text = str(value).strip().lower()

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def clean_identifier(value: Any) -> str:
    """
    Normalize an identifier such as listing ID or VIN.
    """

    value = clean(value)

    if not value:
        return ""

    # Remove spaces and common separators.
    value = re.sub(
        r"[\s_\-/]+",
        "",
        value,
    )

    return value


def clean_url(value: Any) -> str:
    """
    Normalize a source URL for duplicate comparison.
    """

    value = clean(value)

    if not value:
        return ""

    # Remove trailing slash.
    value = value.rstrip("/")

    # Remove common tracking parameters.
    value = re.sub(
        r"[?&](utm_[^=&]+|fbclid|gclid)=[^&]*",
        "",
        value,
        flags=re.I,
    )

    return value


def normalize_text(value: Any) -> str:
    """
    Normalize general text used in fallback fingerprints.
    """

    value = clean(value)

    if not value:
        return ""

    # Remove punctuation.
    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    # Normalize spaces.
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


# ================================================================
# FIELD EXTRACTION
# ================================================================

def get_field(
    car: dict[str, Any],
    *names: str,
) -> Any:
    """
    Get the first available field from a vehicle record.

    Supports slightly different field naming conventions.
    """

    for name in names:

        if name in car:

            value = car.get(name)

            if value is not None and value != "":
                return value

    return None


# ================================================================
# STRONG IDENTIFIERS
# ================================================================

def get_source_id(car: dict[str, Any]) -> str:
    """
    Extract the strongest available listing identifier.
    """

    value = get_field(
        car,
        "source_id",
        "stock_id",
        "listing_id",
        "vehicle_id",
        "id",
    )

    return clean_identifier(value)


def get_vin(car: dict[str, Any]) -> str:
    """
    Extract VIN when available.
    """

    value = get_field(
        car,
        "vin",
        "VIN",
        "vehicle_vin",
    )

    return clean_identifier(value)


def get_source_url(car: dict[str, Any]) -> str:
    """
    Extract and normalize source URL.
    """

    value = get_field(
        car,
        "source_url",
        "listing_url",
        "url",
        "vehicle_url",
    )

    return clean_url(value)


# ================================================================
# VEHICLE FALLBACK FINGERPRINT
# ================================================================

def build_vehicle_fingerprint(
    car: dict[str, Any],
) -> str:
    """
    Build a fallback identity from vehicle information.

    This is used only when a strong listing ID, VIN, or source URL
    is unavailable.
    """

    year = normalize_text(
        get_field(
            car,
            "year",
            "vehicle_year",
            "model_year",
        )
    )

    make = normalize_text(
        get_field(
            car,
            "make",
            "manufacturer",
            "brand",
        )
    )

    model = normalize_text(
        get_field(
            car,
            "model",
            "vehicle_model",
        )
    )

    variant = normalize_text(
        get_field(
            car,
            "variant",
            "trim",
            "version",
        )
    )

    mileage = normalize_text(
        get_field(
            car,
            "mileage",
            "kms",
            "kilometers",
            "odometer",
        )
    )

    price = normalize_text(
        get_field(
            car,
            "price",
            "selling_price",
            "asking_price",
            "list_price",
        )
    )

    colour = normalize_text(
        get_field(
            car,
            "colour",
            "color",
            "exterior_color",
        )
    )

    transmission = normalize_text(
        get_field(
            car,
            "transmission",
            "gearbox",
            "gearbox_type",
        )
    )

    fuel = normalize_text(
        get_field(
            car,
            "fuel",
            "fuel_type",
            "engine_type",
        )
    )

    values = [
        year,
        make,
        model,
        variant,
        mileage,
        price,
        colour,
        transmission,
        fuel,
    ]

    # If practically no identifying information exists,
    # don't create a meaningless fingerprint.
    meaningful_values = [
        value
        for value in values
        if value
    ]

    if len(meaningful_values) < 2:
        return ""

    raw_fingerprint = "|".join(values)

    return raw_fingerprint


def hash_fingerprint(
    fingerprint: str,
) -> str:
    """
    Convert a fingerprint into a stable SHA-256 hash.
    """

    return hashlib.sha256(
        fingerprint.encode("utf-8")
    ).hexdigest()


# ================================================================
# UNIQUE KEY
# ================================================================

def get_unique_key(
    car: dict[str, Any],
) -> tuple[Optional[str], str]:
    """
    Determine the best duplicate-detection key.

    Priority:
        1. VIN
        2. Source/listing ID
        3. Source URL
        4. Vehicle fingerprint

    Returns:
        (key, detection_method)
    """

    # ------------------------------------------------------------
    # 1. VIN
    # ------------------------------------------------------------

    vin = get_vin(car)

    if vin:

        return (
            f"vin:{vin}",
            "vin",
        )

    # ------------------------------------------------------------
    # 2. Source/listing ID
    # ------------------------------------------------------------

    source_id = get_source_id(car)

    if source_id:

        return (
            f"id:{source_id}",
            "source_id",
        )

    # ------------------------------------------------------------
    # 3. Source URL
    # ------------------------------------------------------------

    source_url = get_source_url(car)

    if source_url:

        return (
            f"url:{source_url}",
            "source_url",
        )

    # ------------------------------------------------------------
    # 4. Vehicle fingerprint
    # ------------------------------------------------------------

    fingerprint = build_vehicle_fingerprint(car)

    if fingerprint:

        return (
            f"fingerprint:{hash_fingerprint(fingerprint)}",
            "vehicle_fingerprint",
        )

    # No reliable identity.
    return (
        None,
        "unknown",
    )


# ================================================================
# DUPLICATE METADATA
# ================================================================

def add_duplicate_metadata(
    car: dict[str, Any],
    duplicate_of: Optional[int],
    key: Optional[str],
    method: str,
) -> dict[str, Any]:
    """
    Add duplicate information without destroying original fields.

    A copy of the record is returned.
    """

    result = dict(car)

    result["_duplicate"] = True
    result["_duplicate_of_index"] = duplicate_of
    result["_duplicate_key"] = key
    result["_duplicate_method"] = method

    return result


# ================================================================
# MAIN DUPLICATE DETECTION
# ================================================================

def detect_duplicates(
    cars: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """
    Detect duplicate vehicle advertisements.

    Args:
        cars:
            List of vehicle dictionaries.

    Returns:
        unique cars,
        duplicate cars,
        report
    """

    unique_cars: list[dict[str, Any]] = []
    duplicate_cars: list[dict[str, Any]] = []

    # key -> index of first occurrence in original input
    seen: dict[str, int] = {}

    method_counts = {
        "vin": 0,
        "source_id": 0,
        "source_url": 0,
        "vehicle_fingerprint": 0,
        "unknown": 0,
    }

    invalid_records = 0

    for number, car in enumerate(
        cars,
        start=1,
    ):

        if not isinstance(
            car,
            dict,
        ):

            invalid_records += 1

            logger.warning(
                "[%d] Skipping non-dictionary record.",
                number,
            )

            continue

        key, method = get_unique_key(car)

        method_counts[method] = (
            method_counts.get(method, 0) + 1
        )

        # --------------------------------------------------------
        # No identity available
        # --------------------------------------------------------

        if not key:

            logger.warning(
                "[%d] Could not determine reliable identity.",
                number,
            )

            # Do NOT incorrectly classify an unknown record as
            # a duplicate. Preserve it as unique so that data
            # is not silently lost.
            unique_cars.append(car)

            continue

        # --------------------------------------------------------
        # Duplicate
        # --------------------------------------------------------

        if key in seen:

            first_index = seen[key]

            duplicate_record = add_duplicate_metadata(
                car=car,
                duplicate_of=first_index,
                key=key,
                method=method,
            )

            duplicate_cars.append(
                duplicate_record
            )

            logger.warning(
                "[DUPLICATE] record=%d "
                "duplicate_of=%d "
                "method=%s "
                "key=%s",
                number,
                first_index,
                method,
                key,
            )

            continue

        # --------------------------------------------------------
        # First occurrence
        # --------------------------------------------------------

        seen[key] = number

        unique_cars.append(car)

        logger.info(
            "[UNIQUE] record=%d method=%s key=%s",
            number,
            method,
            key,
        )

    # ------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------

    total_records = len(cars)

    duplicate_count = len(
        duplicate_cars
    )

    unique_count = len(
        unique_cars
    )

    report = {
        "total_records": total_records,
        "unique_records": unique_count,
        "duplicate_records": duplicate_count,
        "invalid_records": invalid_records,
        "duplicate_rate_percent": (
            round(
                (
                    duplicate_count
                    / total_records
                ) * 100,
                2,
            )
            if total_records
            else 0.0
        ),
        "detection_methods": method_counts,
    }

    return (
        unique_cars,
        duplicate_cars,
        report,
    )


# ================================================================
# MAIN
# ================================================================

def main() -> None:
    """
    Run duplicate detection pipeline.
    """

    logger.info(
        "=" * 70
    )

    logger.info(
        "DUPLICATE CHECKER"
    )

    logger.info(
        "=" * 70
    )

    # ------------------------------------------------------------
    # Load input
    # ------------------------------------------------------------

    try:

        cars = load_json(
            INPUT_FILE
        )

    except Exception as error:

        logger.error(
            "Could not load input: %s",
            error,
        )

        return

    # ------------------------------------------------------------
    # Validate input
    # ------------------------------------------------------------

    if not isinstance(
        cars,
        list,
    ):

        logger.error(
            "Input file must contain a JSON list."
        )

        return

    logger.info(
        "Loaded %d records.",
        len(cars),
    )

    # ------------------------------------------------------------
    # Detect duplicates
    # ------------------------------------------------------------

    (
        unique_cars,
        duplicate_cars,
        report,
    ) = detect_duplicates(
        cars
    )

    # ------------------------------------------------------------
    # Save unique records
    # ------------------------------------------------------------

    try:

        save_json(
            OUTPUT_FILE,
            unique_cars,
        )

        logger.info(
            "Unique advertisements saved: %s",
            OUTPUT_FILE,
        )

    except Exception as error:

        logger.error(
            "Failed to save unique advertisements: %s",
            error,
        )

        return

    # ------------------------------------------------------------
    # Save duplicates
    # ------------------------------------------------------------

    try:

        save_json(
            DUPLICATES_FILE,
            duplicate_cars,
        )

        logger.info(
            "Duplicate advertisements saved: %s",
            DUPLICATES_FILE,
        )

    except Exception as error:

        logger.error(
            "Failed to save duplicates: %s",
            error,
        )

    # ------------------------------------------------------------
    # Save report
    # ------------------------------------------------------------

    try:

        save_json(
            REPORT_FILE,
            report,
        )

        logger.info(
            "Duplicate report saved: %s",
            REPORT_FILE,
        )

    except Exception as error:

        logger.error(
            "Failed to save duplicate report: %s",
            error,
        )

    # ------------------------------------------------------------
    # Final statistics
    # ------------------------------------------------------------

    logger.info(
        "=" * 70
    )

    logger.info(
        "Input records       : %d",
        report["total_records"],
    )

    logger.info(
        "Unique records      : %d",
        report["unique_records"],
    )

    logger.info(
        "Duplicate records   : %d",
        report["duplicate_records"],
    )

    logger.info(
        "Invalid records     : %d",
        report["invalid_records"],
    )

    logger.info(
        "Duplicate rate      : %.2f%%",
        report["duplicate_rate_percent"],
    )

    logger.info(
        "Detection methods   : %s",
        report["detection_methods"],
    )

    logger.info(
        "Unique output       : %s",
        OUTPUT_FILE,
    )

    logger.info(
        "Duplicates output   : %s",
        DUPLICATES_FILE,
    )

    logger.info(
        "Report output       : %s",
        REPORT_FILE,
    )

    logger.info(
        "=" * 70
    )


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":
    main()