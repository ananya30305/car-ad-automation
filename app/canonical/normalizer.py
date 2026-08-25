"""Normalize raw source records into CanonicalVehicle instances."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.canonical.models import CanonicalVehicle
from app.canonical.extractor import enrich_from_text, parse_title_parts

BAD_VALUES = {".", "n/a", "na", "unknown", "null", "none", "test", "-", "—"}


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text or text.casefold() in BAD_VALUES:
        return None
    return text


def normalize_condition(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    if text.startswith("https://schema.org/"):
        text = text.rsplit("/", 1)[-1].replace("Condition", "")
    lowered = text.casefold()
    if "used" in lowered:
        return "Used"
    if "new" in lowered:
        return "New"
    if "refurb" in lowered:
        return "Refurbished"
    return text.title()


def normalize_price(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    try:
        price = int(digits)
    except ValueError:
        return None
    return price if price > 0 else None


def normalize_mileage(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    text = str(value)
    match = re.search(r"([\d][\d\s,]{0,12})\s*(?:km|kilometers|kilometres)?", text, re.I)
    if not match:
        digits = re.sub(r"[^\d]", "", text)
    else:
        digits = re.sub(r"[^\d]", "", match.group(1))
    if not digits:
        return None
    try:
        mileage = int(digits)
    except ValueError:
        return None
    return mileage if 0 <= mileage <= 10_000_000 else None


def normalize_year(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    match = re.search(r"(?:19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group())
    return year if 1900 <= year <= 2050 else None


def normalize_seats(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    match = re.search(r"(\d+)", str(value))
    if not match:
        return None
    seats = int(match.group(1))
    return seats if 1 <= seats <= 12 else None


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    items: list[Any]
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        if "•" in value or "\n" in value:
            items = re.split(r"[\n•]+", value)
        else:
            items = re.split(r"[,;|]", value)
    else:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = clean_text(item)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def normalize_phone(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    if text.startswith("+"):
        normalized = "+" + re.sub(r"[^\d]", "", text[1:])
    else:
        normalized = re.sub(r"[^\d]", "", text)
    digits = re.sub(r"[^\d]", "", normalized)
    if len(digits) < 7:
        return None
    return normalized


def normalize_drive_type(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.casefold().replace(" ", "")
    mapping = {
        "fwd": "FWD",
        "frontwheeldrive": "FWD",
        "front-wheeldrive": "FWD",
        "rwd": "RWD",
        "rearwheeldrive": "RWD",
        "rear-wheeldrive": "RWD",
        "awd": "AWD",
        "4wd": "4WD",
        "4x4": "4x4",
        "4x2": "4x2",
        "twowheeldrive": "4x2",
        "fourwheeldrive": "4x4",
    }
    for key, mapped in mapping.items():
        if key in lowered:
            return mapped
    return text


def normalize_transmission(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.casefold()
    if "auto" in lowered or "steptronic" in lowered or "s tronic" in lowered or "dct" in lowered:
        return "Automatic"
    if "manual" in lowered:
        return "Manual"
    if "cvt" in lowered:
        return "CVT"
    return text.title()


def normalize_fuel(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.casefold()
    for token, mapped in (
        ("diesel", "Diesel"),
        ("petrol", "Petrol"),
        ("gasoline", "Petrol"),
        ("hybrid", "Hybrid"),
        ("electric", "Electric"),
        ("lpg", "LPG"),
        ("cng", "CNG"),
    ):
        if token in lowered:
            return mapped
    return text.title()


def normalize_colour(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    # Keep full colour names such as "Black Sapphire Metal"
    return text


def _first(*values: Any) -> Any:
    for value in values:
        if value is None or value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def canonicalize_record(raw: dict[str, Any]) -> CanonicalVehicle:
    """Convert a scraped / inventory dict into a CanonicalVehicle."""
    listing_id = clean_text(
        _first(raw.get("id"), raw.get("listing_id"), raw.get("source_id"), raw.get("stock_id"))
    )
    if not listing_id:
        raise ValueError("Record is missing id / listing_id")

    title = clean_text(_first(raw.get("title"), raw.get("name"), raw.get("listing_title")))
    title_description = clean_text(
        _first(raw.get("title_description"), raw.get("variant"), raw.get("trim"))
    )
    year = normalize_year(_first(raw.get("year"), raw.get("model_year"), raw.get("productionDate")))
    make = clean_text(_first(raw.get("make"), raw.get("brand"), raw.get("manufacturer")))
    model = clean_text(_first(raw.get("model")))
    variant = clean_text(_first(raw.get("variant"), title_description))

    # Title decomposition when structured make/model missing
    parsed = parse_title_parts(title)
    year = year or parsed.get("year")
    make = make or parsed.get("make")
    model = model or parsed.get("model")
    variant = variant or parsed.get("variant")

    description = clean_text(_first(raw.get("description"), raw.get("notes"), raw.get("details")))
    features = normalize_list(raw.get("features"))
    highlights = normalize_list(
        _first(raw.get("highlights"), raw.get("key_features"), raw.get("selling_points"))
    )

    vehicle = CanonicalVehicle(
        id=listing_id,
        source_url=clean_text(raw.get("source_url")),
        title=title,
        year=year,
        make=make,
        model=model,
        variant=variant,
        price=normalize_price(_first(raw.get("price"), raw.get("pricing_summary"), raw.get("asking_price"))),
        mileage=normalize_mileage(_first(raw.get("mileage"), raw.get("kilometers"), raw.get("kms"))),
        transmission=normalize_transmission(raw.get("transmission")),
        fuel=normalize_fuel(_first(raw.get("fuel"), raw.get("fuel_type"))),
        drive_type=normalize_drive_type(_first(raw.get("drive_type"), raw.get("drivetrain"))),
        colour=normalize_colour(_first(raw.get("colour"), raw.get("color"))),
        condition=normalize_condition(raw.get("condition")) or "Used",
        seats=normalize_seats(raw.get("seats")),
        features=features,
        highlights=highlights,
        images=[],  # filled by image preparation
        description=description,
        contact_number=normalize_phone(_first(raw.get("contact_number"), raw.get("phone"), raw.get("mobile"))),
        location=clean_text(_first(raw.get("location"), raw.get("city"), raw.get("area"))),
        country=clean_text(_first(raw.get("country"), raw.get("addressCountry"))),
        dealer_name=clean_text(_first(raw.get("dealer_name"), raw.get("seller_name"), raw.get("dealer"))),
        dealer_address=clean_text(
            _first(raw.get("dealer_address"), raw.get("address"), raw.get("seller_address"))
        ),
        dealer_rating=clean_text(raw.get("dealer_rating")),
        title_description=title_description or variant,
        pricing_summary=clean_text(raw.get("pricing_summary"))
        or (str(normalize_price(_first(raw.get("price"), raw.get("pricing_summary")))) if normalize_price(_first(raw.get("price"), raw.get("pricing_summary"))) else None),
        currency=clean_text(raw.get("currency")) or "ZAR",
    )

    # Keep country and location separate. Default country only when clearly SA inventory.
    if not vehicle.country and vehicle.location and vehicle.location.casefold() == "south africa":
        vehicle.country = "South Africa"
        # location remains a place/area if we later enrich; do not wipe country into location
    if vehicle.location and vehicle.location.casefold() == "south africa" and vehicle.country == "South Africa":
        # Prefer country for the nation; leave location unset until a city/area is known
        vehicle.location = None

    # Description / text fallback for still-missing structured fields
    enrich_from_text(vehicle)

    if not vehicle.title and vehicle.year and vehicle.make and vehicle.model:
        vehicle.title = f"{vehicle.year} {vehicle.make} {vehicle.model}".strip()

    return vehicle
