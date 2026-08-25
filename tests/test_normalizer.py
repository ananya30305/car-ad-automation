"""Tests for canonicalization / title parsing / description fallback."""

from __future__ import annotations

from app.canonical.extractor import parse_title_parts
from app.canonical.normalizer import canonicalize_record


SAMPLE = {
    "listing_id": "11195371",
    "source_url": "https://www.cars.co.za/for-sale/used/2025-BMW-X3/11195371/",
    "title": "2025 BMW X3",
    "title_description": "sDrive 20i",
    "condition": "https://schema.org/UsedCondition",
    "year": None,
    "mileage": None,
    "transmission": None,
    "fuel": None,
    "drive_type": None,
    "colour": None,
    "seats": None,
    "features": [],
    "highlights": [],
    "price": 989900,
    "location": "South Africa",
    "description": (
        "Sophisticated, spacious and rewarding to drive, this 2025 BMW X3 20 brings premium SUV "
        "appeal in Black Sapphire Metal. Its 2.0-litre petrol engine works with an automatic "
        "Steptronic transmission, while rear-wheel drive adds a balanced feel. With only "
        "11 095 km covered. Inside, the X3 offers seating for five. "
        "Key Features: • Black Sapphire Metal exterior • Automatic Steptronic transmission "
        "• Active/adaptive cruise control • LED headlights • Navigation • Head-up display"
    ),
}


def test_title_parsing():
    parts = parse_title_parts("2020 Toyota Corolla 1.8 XS")
    assert parts["year"] == 2020
    assert parts["make"] == "Toyota"
    assert parts["model"] == "Corolla"
    assert parts["variant"] == "1.8 XS"


def test_description_fallback_populates_fields():
    vehicle = canonicalize_record(SAMPLE)
    assert vehicle.year == 2025
    assert vehicle.make == "BMW"
    assert vehicle.model == "X3"
    assert vehicle.mileage == 11095
    assert vehicle.transmission == "Automatic"
    assert vehicle.fuel == "Petrol"
    assert vehicle.drive_type == "RWD"
    assert vehicle.colour is not None
    assert vehicle.seats == 5
    assert len(vehicle.features) >= 3
    assert len(vehicle.highlights) >= 1
    assert vehicle.condition == "Used"
    # country/location separation
    assert vehicle.country == "South Africa"
    assert vehicle.location != vehicle.country


def test_does_not_invent_contact():
    vehicle = canonicalize_record(SAMPLE)
    assert vehicle.contact_number is None
