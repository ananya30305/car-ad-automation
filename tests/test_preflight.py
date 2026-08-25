"""Unit tests for preflight validation (no live website)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.canonical.models import CanonicalVehicle
from app.validation.dropdowns import map_dropdown_value
from app.validation.preflight import validate_vehicle


def _make_images(tmp_path: Path, count: int) -> list[str]:
    paths: list[str] = []
    for index in range(count):
        path = tmp_path / f"img_{index}.jpg"
        # Distinct pixel colour so files are not byte-identical
        Image.new("RGB", (64, 64), color=(index * 40 % 255, 80, 120)).save(path, format="JPEG")
        paths.append(str(path))
    return paths


def _valid_vehicle(tmp_path: Path, **overrides) -> CanonicalVehicle:
    data = dict(
        id="TEST1",
        source_url="https://example.test/cars/TEST1",
        title="2020 Toyota Corolla 1.8 XS",
        year=2020,
        make="Toyota",
        model="Corolla",
        variant="1.8 XS",
        price=250000,
        mileage=45000,
        transmission="Automatic",
        fuel="Petrol",
        drive_type="FWD",
        colour="Silver",
        condition="Used",
        seats=5,
        features=["Aircon", "ABS", "Bluetooth"],
        highlights=["Low mileage"],
        images=_make_images(tmp_path, 5),
        description="A well maintained 2020 Toyota Corolla with service history.",
        contact_number="0821234567",
        location="Cape Town",
        country="South Africa",
        dealer_name="Test Motors",
        dealer_address="1 Main Road",
        dealer_rating="4.5",
        category_path=["Vehicles", "Cars - Parts", "Used cars in South Africa"],
    )
    data.update(overrides)
    return CanonicalVehicle(**data)


def test_valid_canonical_vehicle_passes(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path))
    assert result.valid is True
    assert result.errors == []


def test_missing_year_fails(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, year=None))
    assert result.valid is False
    assert any("year" in e for e in result.errors)


def test_missing_mileage_fails(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, mileage=None))
    assert result.valid is False
    assert any("mileage" in e for e in result.errors)


def test_fewer_than_3_features_fails(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, features=["Only one", "Only two"]))
    assert result.valid is False
    assert any("features" in e for e in result.errors)


def test_missing_highlight_fails(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, highlights=[]))
    assert result.valid is False
    assert any("highlights" in e for e in result.errors)


def test_fewer_than_5_images_fails(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, images=_make_images(tmp_path, 2)))
    assert result.valid is False
    assert any("images" in e for e in result.errors)


def test_six_images_rejected(tmp_path: Path):
    result = validate_vehicle(_valid_vehicle(tmp_path, images=_make_images(tmp_path, 6)))
    assert result.valid is False
    assert any("exactly 5" in e for e in result.errors)


def test_dropdown_normalization_works():
    mapped, error = map_dropdown_value("fuel", "Gasoline")
    assert error is None
    assert mapped == "Petrol"
    mapped, error = map_dropdown_value("transmission", "Auto")
    assert error is None
    assert mapped == "Automatic"


def test_invalid_dropdown_value_rejected():
    mapped, error = map_dropdown_value("fuel", "Banana")
    assert mapped is None
    assert error is not None
    assert "Banana" in error


def test_country_and_location_remain_separate(tmp_path: Path):
    vehicle = _valid_vehicle(tmp_path, country="South Africa", location="South Africa")
    result = validate_vehicle(vehicle)
    assert result.valid is False
    assert any("country and location" in e for e in result.errors)

    ok = _valid_vehicle(tmp_path, country="South Africa", location="Cape Town")
    assert validate_vehicle(ok).valid is True
