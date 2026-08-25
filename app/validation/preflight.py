"""Hard preflight validation — single authority before Playwright."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from app import config
from app.canonical.models import CanonicalVehicle
from app.validation.dropdowns import map_dropdown_value


@dataclass
class PreflightResult:
    id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mapped_values: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REQUIRED_PRESENT = (
    "year",
    "make",
    "model",
    "price",
    "mileage",
    "transmission",
    "fuel",
    "drive_type",
    "colour",
    "seats",
    "contact_number",
    "dealer_name",
    "dealer_address",
    "source_url",
)


def _image_ok(path_str: str) -> bool:
    path = Path(path_str)
    return path.is_file() and path.stat().st_size > 0


def validate_vehicle(vehicle: CanonicalVehicle) -> PreflightResult:
    errors: list[str] = []
    warnings: list[str] = []
    mapped: dict[str, Any] = {}

    for field_name in REQUIRED_PRESENT:
        value = getattr(vehicle, field_name, None)
        if value is None or value == "":
            errors.append(f"{field_name} is missing")

    if not vehicle.description or len(vehicle.description) < 20:
        errors.append("description is missing or too short")

    features = [f for f in vehicle.features if f and str(f).strip()]
    highlights = [h for h in vehicle.highlights if h and str(h).strip()]
    if len(features) < config.MIN_FEATURES:
        errors.append(f"features requires at least {config.MIN_FEATURES} items")
    if len(highlights) < config.MIN_HIGHLIGHTS:
        errors.append(f"highlights requires at least {config.MIN_HIGHLIGHTS} items")

    images = list(vehicle.images or [])
    usable = [img for img in images if _image_ok(img)]
    if len(images) > config.REQUIRED_IMAGES:
        errors.append(
            f"exactly {config.REQUIRED_IMAGES} images required "
            f"(found {len(images)}; trim before preflight)"
        )
    elif len(usable) != config.REQUIRED_IMAGES:
        errors.append(
            f"exactly {config.REQUIRED_IMAGES} usable local images required "
            f"(found {len(usable)})"
        )
    elif len(set(Path(img).resolve() for img in usable)) != config.REQUIRED_IMAGES:
        errors.append("images must be unique files (no duplicates)")

    # Category must match the fixed destination path
    expected = list(config.CATEGORY_PATH_LABELS)
    if list(vehicle.category_path) != expected:
        errors.append(
            f"category_path must be {expected} (got {vehicle.category_path})"
        )

    # Country / location must remain separate concepts
    if vehicle.country and vehicle.location and vehicle.country == vehicle.location:
        errors.append("country and location must not be the same field value")

    if not vehicle.dealer_rating:
        warnings.append("dealer_rating is missing (destination field is required)")

    # Explicit dropdown mapping when destination uses selects
    for field_name in ("transmission", "fuel", "condition", "drive_type", "colour"):
        value = getattr(vehicle, field_name, None)
        if value in (None, ""):
            continue
        mapped_value, map_error = map_dropdown_value(field_name, value)
        if map_error:
            errors.append(map_error)
        elif mapped_value is not None:
            mapped[field_name] = mapped_value

    return PreflightResult(
        id=vehicle.id,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        mapped_values=mapped,
    )


def validate_or_reject(
    vehicle: CanonicalVehicle,
) -> tuple[bool, PreflightResult]:
    result = validate_vehicle(vehicle)
    return result.valid, result
