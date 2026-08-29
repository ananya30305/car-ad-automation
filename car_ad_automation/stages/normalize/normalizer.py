"""Data normalization layer for vehicle records.

Converts raw CSV/JSON vehicle records into the canonical Vehicle
model used by the rest of the automation pipeline.
"""

import re
from pathlib import Path
from typing import Any, Optional

from car_ad_automation.core.models import Vehicle


# ============================================================
# FIELD MAPPING
# ============================================================

# Alternative source names -> canonical Vehicle field name.
#
# Matching is case-insensitive because normalize_field_name()
# converts keys to lowercase first.

FIELD_MAPPING = {

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    "stock_id": "id",
    "stockid": "id",
    "listing_id": "id",
    "listingid": "id",
    "vehicle_id": "id",
    "vehicleid": "id",
    "inventory_id": "id",
    "inventoryid": "id",
    "reference": "id",
    "reference_number": "id",
    "ref": "id",
    "vin": "id",

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    "listing_title": "title",
    "listingtitle": "title",
    "vehicle_title": "title",
    "vehicletitle": "title",
    "vehicle_name": "title",
    "vehiclename": "title",
    "name": "title",
    "ad_title": "title",
    "advertisement_title": "title",

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    "selling_price": "price",
    "sellingprice": "price",
    "asking_price": "price",
    "askingprice": "price",
    "list_price": "price",
    "listprice": "price",
    "sale_price": "price",
    "saleprice": "price",
    "amount": "price",
    "cost": "price",

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    "vehicle_year": "year",
    "vehicleyear": "year",
    "manufacture_year": "year",
    "manufacturing_year": "year",
    "model_year": "year",
    "year_of_manufacture": "year",
    "year_manufactured": "year",
    "yom": "year",

    # --------------------------------------------------------
    # MILEAGE
    # --------------------------------------------------------

    "kms": "mileage",
    "km": "mileage",
    "kilometer": "mileage",
    "kilometers": "mileage",
    "kilometres": "mileage",
    "kilometer_driven": "mileage",
    "kilometers_driven": "mileage",
    "kilometres_driven": "mileage",
    "mileage_km": "mileage",
    "odometer": "mileage",
    "odometer_reading": "mileage",
    "distance": "mileage",

    # --------------------------------------------------------
    # TRANSMISSION
    # --------------------------------------------------------

    "gearbox": "transmission",
    "gearbox_type": "transmission",
    "transmission_type": "transmission",
    "transmissiontype": "transmission",
    "gear_type": "transmission",

    # --------------------------------------------------------
    # FUEL
    # --------------------------------------------------------

    "fuel_type": "fuel",
    "fueltype": "fuel",
    "engine_type": "fuel",
    "fuel_used": "fuel",

    # --------------------------------------------------------
    # DRIVE TYPE
    # --------------------------------------------------------

    "drivetrain": "drive_type",
    "drive": "drive_type",
    "drive_train": "drive_type",
    "drive_type_name": "drive_type",

    # --------------------------------------------------------
    # COLOUR
    # --------------------------------------------------------

    "color": "colour",
    "paint_color": "colour",
    "paint_colour": "colour",
    "exterior_color": "colour",
    "exterior_colour": "colour",
    "body_color": "colour",
    "body_colour": "colour",

    # --------------------------------------------------------
    # SEATS
    # --------------------------------------------------------

    "seat_count": "seats",
    "number_of_seats": "seats",
    "num_seats": "seats",

    # --------------------------------------------------------
    # CONDITION
    # --------------------------------------------------------

    "vehicle_condition": "condition",
    "car_condition": "condition",
    "condition_type": "condition",

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    "notes": "description",
    "remarks": "description",
    "comments": "description",
    "details": "description",
    "summary": "description",
    "vehicle_description": "description",
    "listing_description": "description",
    "ad_description": "description",

    # --------------------------------------------------------
    # PHONE / CONTACT
    # --------------------------------------------------------

    "phone": "contact_number",
    "mobile": "contact_number",
    "telephone": "contact_number",
    "telephone_number": "contact_number",
    "phone_number": "contact_number",
    "mobile_number": "contact_number",
    "contact": "contact_number",
    "contact_phone": "contact_number",
    "dealer_phone": "contact_number",
    "dealer_mobile": "contact_number",
    "seller_phone": "contact_number",
    "seller_mobile": "contact_number",

    # --------------------------------------------------------
    # DEALER
    # --------------------------------------------------------

    "dealer": "dealer_name",
    "dealername": "dealer_name",
    "seller_name": "dealer_name",
    "seller": "dealer_name",
    "sellername": "dealer_name",
    "company": "dealer_name",
    "company_name": "dealer_name",

    # --------------------------------------------------------
    # DEALER ADDRESS
    # --------------------------------------------------------

    "seller_address": "dealer_address",
    "seller_location": "dealer_address",
    "dealer_location": "dealer_address",
    "dealeraddress": "dealer_address",
    "selleraddress": "dealer_address",
    "address": "dealer_address",

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    "city": "location",
    "town": "location",
    "area": "location",
    "suburb": "location",
    "region": "location",
    "location_name": "location",

    # --------------------------------------------------------
    # IMAGES
    # --------------------------------------------------------

    "image_urls": "images",
    "image_url": "images",
    "image_paths": "images",
    "image_path": "images",
    "image_folder": "images",
    "images_folder": "images",
    "photo": "images",
    "photos": "images",
    "picture": "images",
    "pictures": "images",
    "vehicle_images": "images",
    "vehicle_photos": "images",

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    "key_features": "features",
    "vehicle_features": "features",
    "optional_features": "features",
    "equipment": "features",
    "specifications": "features",

    # --------------------------------------------------------
    # HIGHLIGHTS
    # --------------------------------------------------------

    "selling_points": "highlights",
    "key_highlights": "highlights",
    "vehicle_highlights": "highlights",
    "highlights_points": "highlights",

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    "source": "source_id",
    "source_record_id": "source_id",
    "source_vehicle_id": "source_id",

    # --------------------------------------------------------
    # CURRENCY
    # --------------------------------------------------------

    "currency_code": "currency",
    "price_currency": "currency",

    # --------------------------------------------------------
    # CREATED DATE
    # --------------------------------------------------------

    "created": "created_at",
    "created_date": "created_at",
    "date_created": "created_at",
}


# ============================================================
# FIELD NAME NORMALIZATION
# ============================================================

def normalize_field_name(field: str) -> str:
    """
    Normalize a raw field/column name.

    Examples:
        "Stock ID"       -> "id"
        "stock_id"       -> "id"
        "Selling Price"  -> "price"
        "Vehicle Year"   -> "year"

    Args:
        field:
            Raw field name.

    Returns:
        Canonical field name.
    """

    if field is None:
        return ""

    field_lower = str(field).strip().lower()

    # Replace spaces, hyphens and repeated separators.
    field_lower = re.sub(
        r"[\s\-\/]+",
        "_",
        field_lower,
    )

    # Remove characters that are not useful in field names.
    field_lower = re.sub(
        r"[^a-z0-9_]",
        "",
        field_lower,
    )

    # Collapse repeated underscores.
    field_lower = re.sub(
        r"_+",
        "_",
        field_lower,
    ).strip("_")

    return FIELD_MAPPING.get(
        field_lower,
        field_lower,
    )


# ============================================================
# STRING NORMALIZATION
# ============================================================

def normalize_string(
    value: Any,
) -> Optional[str]:
    """
    Normalize a string value.

    Removes:
    - leading/trailing whitespace
    - repeated whitespace
    - common CSV null values

    Args:
        value:
            Any source value.

    Returns:
        Clean string or None.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Treat common CSV/JSON null representations as empty.
    if text.lower() in {
        "none",
        "null",
        "nan",
        "n/a",
        "na",
        "-",
    }:
        return None

    # Replace repeated whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text if text else None


# ============================================================
# PRICE NORMALIZATION
# ============================================================

def normalize_price(
    value: Any,
) -> Optional[int]:
    """
    Normalize price to an integer.

    Examples:
        "₹ 5,99,000" -> 599000
        "599000"     -> 599000
        "599,000"    -> 599000
        "$12,500"    -> 12500
        "R 250 000"  -> 250000
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        try:
            number = int(float(value))
            return number if number >= 0 else None
        except (ValueError, TypeError):
            return None

    price_str = str(value).strip()

    if not price_str:
        return None

    # Remove currency symbols/letters while keeping
    # digits, comma and decimal point.
    price_str = re.sub(
        r"[^\d.,]",
        "",
        price_str,
    )

    if not price_str:
        return None

    # --------------------------------------------------------
    # Handle both comma and decimal point.
    # --------------------------------------------------------

    if "," in price_str and "." in price_str:

        last_comma = price_str.rfind(",")
        last_dot = price_str.rfind(".")

        if last_dot > last_comma:
            # Example:
            # 12,500.50
            price_str = price_str.replace(
                ",",
                "",
            )

        else:
            # Example:
            # 12.500,50
            price_str = (
                price_str
                .replace(".", "")
                .replace(",", ".")
            )

    elif "," in price_str:

        parts = price_str.split(",")

        # A final two-digit group can represent
        # decimal cents.
        if (
            len(parts) == 2
            and len(parts[-1]) == 2
            and len(parts[0]) <= 3
        ):
            price_str = price_str.replace(
                ",",
                ".",
            )
        else:
            # Treat commas as thousands separators.
            price_str = price_str.replace(
                ",",
                "",
            )

    elif price_str.count(".") > 1:

        # Example:
        # 1.250.000
        price_str = price_str.replace(
            ".",
            "",
        )

    try:

        price = float(price_str)

        if price < 0:
            return None

        return int(round(price))

    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# MILEAGE NORMALIZATION
# ============================================================

def normalize_mileage(
    value: Any,
) -> Optional[int]:
    """
    Normalize mileage to integer.

    Examples:
        "12,000 km" -> 12000
        "12 000 Km" -> 12000
        "12000"     -> 12000
        "12,500mi"  -> 12500
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):

        try:
            mileage = int(float(value))

            return (
                mileage
                if mileage >= 0
                else None
            )

        except (
            ValueError,
            TypeError,
        ):
            return None

    mileage_str = str(value).strip()

    if not mileage_str:
        return None

    # Remove common mileage units.
    mileage_str = re.sub(
        r"\s*(km|kms|kilometer|kilometers|"
        r"kilometre|kilometres|miles|mi)\s*$",
        "",
        mileage_str,
        flags=re.IGNORECASE,
    )

    # Keep digits and decimal point.
    mileage_str = re.sub(
        r"[^\d.]",
        "",
        mileage_str,
    )

    if not mileage_str:
        return None

    try:

        mileage = float(
            mileage_str
        )

        if mileage < 0:
            return None

        return int(round(mileage))

    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# YEAR NORMALIZATION
# ============================================================

def normalize_year(
    value: Any,
) -> Optional[int]:
    """
    Normalize vehicle year.

    Accepts values such as:
        "2025"
        2025
        "2025 model"
        "MY 2025"
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    # Extract a four-digit year.
    match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        str(value),
    )

    if not match:
        return None

    try:

        year = int(
            match.group(1)
        )

        if 1900 <= year <= 2050:
            return year

    except (
        ValueError,
        TypeError,
    ):
        pass

    return None


# ============================================================
# SEAT NORMALIZATION
# ============================================================

def normalize_seats(
    value: Any,
) -> Optional[int]:
    """
    Normalize seat count.

    Examples:
        "5"       -> 5
        "5 seats" -> 5
        "7-seater" -> 7
    """

    if value is None:
        return None

    match = re.search(
        r"\b(\d{1,2})\b",
        str(value),
    )

    if not match:
        return None

    try:

        seats = int(
            match.group(1)
        )

        if 1 <= seats <= 12:
            return seats

    except (
        ValueError,
        TypeError,
    ):
        pass

    return None


# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(
    value: Any,
) -> Optional[str]:
    """
    Normalize phone number.

    Important:
    This function never creates a phone number that was not
    present in the source data.
    """

    if value is None:
        return None

    phone_str = str(value).strip()

    if not phone_str:
        return None

    # Preserve a leading + for international numbers.
    if phone_str.startswith("+"):

        digits = re.sub(
            r"\D",
            "",
            phone_str[1:],
        )

        normalized = (
            "+"
            + digits
        )

    else:

        normalized = re.sub(
            r"\D",
            "",
            phone_str,
        )

    digits = re.sub(
        r"\D",
        "",
        normalized,
    )

    # Basic sanity check.
    if len(digits) < 7:
        return None

    return normalized


# ============================================================
# LIST NORMALIZATION
# ============================================================

def normalize_list(
    value: Any,
) -> list[str]:
    """
    Normalize a list of strings.

    Handles:

        ["feature1", "feature2"]

        "feature1, feature2"

        "feature1; feature2"

        "feature1 | feature2"
    """

    if value is None:
        return []

    # --------------------------------------------------------
    # Already a list/tuple/set
    # --------------------------------------------------------

    if isinstance(
        value,
        (list, tuple, set),
    ):

        result = []

        for item in value:

            text = normalize_string(
                item
            )

            if text:
                result.append(text)

        return result

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        # Try common nested list keys.
        for key in (
            "items",
            "values",
            "features",
            "highlights",
            "list",
        ):

            if key in value:

                return normalize_list(
                    value[key]
                )

        return []

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return []

        items = re.split(
            r"[,;|]+",
            text,
        )

        result = []

        for item in items:

            cleaned = normalize_string(
                item
            )

            if cleaned:
                result.append(cleaned)

        return result

    return []


# ============================================================
# IMAGE NORMALIZATION
# ============================================================

def normalize_images(
    value: Any,
) -> list[str]:
    """
    Normalize image paths/URLs.

    Handles:

        ["path1.jpg", "path2.jpg"]

        "path1.jpg,path2.jpg"

        {"folder": "images/123"}

        {"images": [...]}

        {"url": "https://example.com/car.jpg"}
    """

    if value is None:
        return []

    # --------------------------------------------------------
    # List / tuple / set
    # --------------------------------------------------------

    if isinstance(
        value,
        (list, tuple, set),
    ):

        result = []

        for item in value:

            if isinstance(
                item,
                str,
            ):

                cleaned = item.strip()

                if cleaned:
                    result.append(
                        cleaned
                    )

            elif isinstance(
                item,
                dict,
            ):

                if "url" in item:

                    url = normalize_string(
                        item["url"]
                    )

                    if url:
                        result.append(url)

                elif "path" in item:

                    path = normalize_string(
                        item["path"]
                    )

                    if path:
                        result.append(path)

                elif "folder" in item:

                    folder = normalize_string(
                        item["folder"]
                    )

                    if folder:
                        result.append(
                            f"folder:{folder}"
                        )

        return result

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(
        value,
        dict,
    ):

        if "images" in value:

            return normalize_images(
                value["images"]
            )

        if "image_urls" in value:

            return normalize_images(
                value["image_urls"]
            )

        if "url" in value:

            url = normalize_string(
                value["url"]
            )

            return (
                [url]
                if url
                else []
            )

        if "path" in value:

            path = normalize_string(
                value["path"]
            )

            return (
                [path]
                if path
                else []
            )

        if "folder" in value:

            folder = normalize_string(
                value["folder"]
            )

            return (
                [f"folder:{folder}"]
                if folder
                else []
            )

        return []

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(
        value,
        str,
    ):

        text = value.strip()

        if not text:
            return []

        # Support comma, semicolon and pipe separated images.
        items = re.split(
            r"[,;|]+",
            text,
        )

        result = []

        for item in items:

            cleaned = item.strip()

            if cleaned:
                result.append(
                    cleaned
                )

        return result

    return []


# ============================================================
# CONDITION NORMALIZATION
# ============================================================

def normalize_condition(
    value: Any,
) -> str:
    """
    Normalize vehicle condition.

    Returns:
        new
        used
        refurbished

    Unknown values are preserved as cleaned text so the source
    information is not silently destroyed.
    """

    text = normalize_string(
        value
    )

    if not text:
        return "used"

    lowered = text.lower()

    if lowered in {
        "new",
        "brand new",
        "new vehicle",
    }:
        return "new"

    if lowered in {
        "used",
        "pre owned",
        "pre-owned",
        "preowned",
        "second hand",
        "second-hand",
    }:
        return "used"

    if lowered in {
        "refurbished",
        "renewed",
        "reconditioned",
    }:
        return "refurbished"

    return text


# ============================================================
# NORMALIZE RECORD
# ============================================================

def normalize_record(
    record: dict[str, Any],
) -> Vehicle:
    """
    Normalize one raw CSV/JSON record into a Vehicle object.

    Args:
        record:
            Raw input dictionary.

    Returns:
        Vehicle object.

    Raises:
        ValueError:
            If record is not a dictionary.
    """

    if not isinstance(
        record,
        dict,
    ):
        raise ValueError(
            "Vehicle record must be a dictionary"
        )

    # --------------------------------------------------------
    # First normalize all field names.
    # --------------------------------------------------------

    normalized: dict[str, Any] = {}

    for raw_key, value in record.items():

        canonical_name = normalize_field_name(
            str(raw_key)
        )

        if not canonical_name:
            continue

        # Do not overwrite an existing useful value with an
        # empty value.
        if canonical_name in normalized:

            existing = normalized[
                canonical_name
            ]

            if (
                existing is None
                or str(existing).strip() == ""
            ):
                normalized[
                    canonical_name
                ] = value

        else:

            normalized[
                canonical_name
            ] = value

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    vehicle_id = normalize_string(
        normalized.get("id")
    )

    if not vehicle_id:

        vehicle_id = (
            normalize_string(
                normalized.get(
                    "source_id"
                )
            )
        )

    if not vehicle_id:

        # Use a stable-looking fallback based on source data
        # rather than the Python object id.
        source_title = normalize_string(
            normalized.get("title")
        ) or "vehicle"

        source_price = normalize_string(
            normalized.get("price")
        ) or "0"

        fallback_base = (
            f"{source_title}_"
            f"{source_price}"
        )

        fallback_base = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            fallback_base,
        ).strip("_")

        vehicle_id = (
            f"auto_{fallback_base or 'vehicle'}"
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = normalize_string(
        normalized.get("title")
    )

    if not title:
        title = "Untitled Vehicle"

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price = normalize_price(
        normalized.get("price")
    )

    if price is None:
        price = 0

    # --------------------------------------------------------
    # Currency
    # --------------------------------------------------------

    currency = normalize_string(
        normalized.get("currency")
    )

    if not currency:
        currency = "ZAR"

    # --------------------------------------------------------
    # Build Vehicle
    # --------------------------------------------------------

    vehicle = Vehicle(

        # Required
        id=vehicle_id,
        title=title,
        price=price,

        # Vehicle information
        condition=normalize_condition(
            normalized.get(
                "condition"
            )
        ),

        year=normalize_year(
            normalized.get("year")
        ),

        mileage=normalize_mileage(
            normalized.get("mileage")
        ),

        transmission=normalize_string(
            normalized.get(
                "transmission"
            )
        ),

        fuel=normalize_string(
            normalized.get("fuel")
        ),

        drive_type=normalize_string(
            normalized.get(
                "drive_type"
            )
        ),

        colour=normalize_string(
            normalized.get("colour")
        ),

        seats=normalize_seats(
            normalized.get("seats")
        ),

        # Description
        description=normalize_string(
            normalized.get(
                "description"
            )
        ),

        # Dealer / contact
        dealer_name=normalize_string(
            normalized.get(
                "dealer_name"
            )
        ),

        dealer_address=normalize_string(
            normalized.get(
                "dealer_address"
            )
        ),

        contact_number=normalize_phone(
            normalized.get(
                "contact_number"
            )
        ),

        location=normalize_string(
            normalized.get(
                "location"
            )
        ),

        # Features
        features=normalize_list(
            normalized.get(
                "features"
            )
        ),

        highlights=normalize_list(
            normalized.get(
                "highlights"
            )
        ),

        # Images
        images=normalize_images(
            normalized.get(
                "images"
            )
        ),

        # Currency
        currency=currency,

        # Metadata
        source_id=normalize_string(
            normalized.get(
                "source_id"
            )
        ),

        created_at=normalize_string(
            normalized.get(
                "created_at"
            )
        ),
    )

    return vehicle


# ============================================================
# NORMALIZE MULTIPLE RECORDS
# ============================================================

def normalize_records(
    records: list[dict[str, Any]],
) -> list[Vehicle]:
    """
    Normalize multiple raw records.

    Invalid records are skipped instead of stopping the entire
    batch.

    Args:
        records:
            Raw source records.

    Returns:
        List of successfully normalized Vehicle objects.
    """

    vehicles: list[Vehicle] = []

    for record in records:

        try:

            vehicle = normalize_record(
                record
            )

            vehicles.append(
                vehicle
            )

        except Exception:

            # Keep batch processing resilient.
            continue

    return vehicles