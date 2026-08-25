"""Deterministic form filling from canonical records + static form map."""

from __future__ import annotations

import logging
from typing import Any, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from app.canonical.models import CanonicalVehicle
from app.posting.form_map import field_specs, load_form_map
from app.validation.dropdowns import map_dropdown_value

logger = logging.getLogger(__name__)


def _vehicle_value(vehicle: CanonicalVehicle, source_key: str) -> Any:
    if source_key == "features":
        return "\n".join(vehicle.features)
    if source_key == "highlights":
        return "\n".join(vehicle.highlights)
    if source_key == "pricing_summary":
        return vehicle.pricing_summary or (str(vehicle.price) if vehicle.price is not None else None)
    if source_key == "title_description":
        return vehicle.title_description or vehicle.variant or ""
    if source_key == "seats":
        return "" if vehicle.seats is None else str(vehicle.seats)
    if source_key == "year":
        return "" if vehicle.year is None else str(vehicle.year)
    if source_key == "mileage":
        return "" if vehicle.mileage is None else str(vehicle.mileage)
    if source_key == "price":
        return "" if vehicle.price is None else str(vehicle.price)
    return getattr(vehicle, source_key, None)


def select_category(page: Page, form_map: dict[str, Any]) -> list[str]:
    """Select the inspected category cascade. Returns errors."""
    errors: list[str] = []
    category = form_map.get("category") or {}
    path = category.get("path") or []
    selector = category.get("select_selector") or "select#category, select[name='category[]']"

    for step in path:
        value = str(step.get("value"))
        label = step.get("label")
        try:
            # Always target the last visible category select in the cascade
            selects = page.locator(selector)
            count = selects.count()
            if count == 0:
                errors.append(f"Category select not found for step {label} ({value})")
                return errors
            control = selects.nth(count - 1)
            control.wait_for(state="visible", timeout=15000)
            control.select_option(value=value)
            page.wait_for_timeout(800)
        except Exception as error:
            errors.append(f"Failed selecting category {label} ({value}): {error}")
            return errors
    return errors


def fill_mapped_fields(page: Page, vehicle: CanonicalVehicle, form_map: dict[str, Any] | None = None) -> list[str]:
    """Fill only fields that have explicit selectors. No guessing."""
    form_map = form_map or load_form_map()
    errors: list[str] = []
    specs = field_specs(form_map)

    for field_name, spec in specs.items():
        selector = spec.get("selector")
        if not selector:
            errors.append(f"No selector configured for field {field_name}")
            continue
        source_key = spec.get("from") or field_name
        value = _vehicle_value(vehicle, source_key)
        if value in (None, ""):
            # Destination marks many fields required; surface clearly
            if spec.get("required"):
                errors.append(f"Missing value for required field {field_name} (from {source_key})")
            continue

        # Apply explicit dropdown map when options exist
        mapped, map_error = map_dropdown_value(source_key, value)
        if map_error:
            errors.append(map_error)
            continue
        if mapped is not None:
            value = mapped

        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=15000)
            field_type = (spec.get("type") or "text").lower()
            if field_type == "select":
                # Prefer label/text match against explicit option text only
                try:
                    locator.select_option(label=str(value))
                except Exception:
                    locator.select_option(value=str(value))
            else:
                locator.fill(str(value))
        except Exception as error:
            errors.append(f"Could not fill {field_name}: {error}")
    return errors


def upload_images(page: Page, vehicle: CanonicalVehicle, form_map: dict[str, Any] | None = None) -> list[str]:
    form_map = form_map or load_form_map()
    errors: list[str] = []
    images_cfg = form_map.get("images") or {}
    selector = images_cfg.get("file_input_fallback_selector") or "input[type='file']"
    paths = list(vehicle.images)
    if len(paths) != int(images_cfg.get("required_count") or 5):
        return [f"Expected {images_cfg.get('required_count', 5)} images, got {len(paths)}"]
    try:
        locator = page.locator(selector).first
        locator.set_input_files(paths)
    except Exception as error:
        errors.append(f"Image upload failed: {error}")
    return errors


def verify_fields(page: Page, vehicle: CanonicalVehicle, form_map: dict[str, Any] | None = None) -> list[str]:
    """Read back filled values and compare to expected."""
    form_map = form_map or load_form_map()
    errors: list[str] = []
    specs = field_specs(form_map)
    for field_name, spec in specs.items():
        selector = spec.get("selector")
        if not selector:
            continue
        source_key = spec.get("from") or field_name
        expected = _vehicle_value(vehicle, source_key)
        if expected in (None, ""):
            continue
        mapped, _ = map_dropdown_value(source_key, expected)
        if mapped is not None:
            expected = mapped
        try:
            locator = page.locator(selector).first
            field_type = (spec.get("type") or "text").lower()
            if field_type == "select":
                actual = locator.input_value()
                # Compare against selected option label when possible
                selected = locator.locator("option:checked")
                if selected.count():
                    actual_label = selected.first.inner_text().strip()
                    if str(expected) not in (actual, actual_label):
                        errors.append(
                            f"Verify failed for {field_name}: expected {expected!r}, got {actual_label!r}"
                        )
                elif str(expected) != actual:
                    errors.append(
                        f"Verify failed for {field_name}: expected {expected!r}, got {actual!r}"
                    )
            else:
                actual = locator.input_value()
                if str(expected).strip() != str(actual).strip():
                    errors.append(
                        f"Verify failed for {field_name}: expected {expected!r}, got {actual!r}"
                    )
        except PlaywrightTimeout:
            errors.append(f"Verify timeout for {field_name}")
        except Exception as error:
            errors.append(f"Verify error for {field_name}: {error}")
    return errors
