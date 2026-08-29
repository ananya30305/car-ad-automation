"""Dry-run browser workflow. It fills only after explicit form-option mapping."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from car_ad_automation.stages.post.automation.form_mapper import map_vehicle
from car_ad_automation.stages.post.automation.validator import validate_form_record

logger = logging.getLogger(__name__)


def load_record(path: Path, index: int = 0) -> dict[str, Any]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Dataset contains no vehicle records")
    record = records[index]
    if not isinstance(record, dict):
        raise ValueError("Vehicle record is not an object")
    return record


def dry_run(record: dict[str, Any], form_options: dict[str, list[str]]) -> dict[str, Any]:
    mapped, mapping_errors = map_vehicle(record, form_options)
    errors = mapping_errors + validate_form_record(mapped)
    result = {"status": "FORM_FILLED" if not errors else "BLOCKED", "dry_run": True, "source_url": record.get("source_url"), "mapped": mapped, "errors": list(dict.fromkeys(errors))}
    logger.info("DRY_RUN %s: %s", result["status"], record.get("source_url"))
    return result


def fill_form_dry_run(page: Any, mapped: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    field_labels = {"title": "Title", "description": "Description", "price": "Price", "mileage": "Mileage"}
    for field, label in field_labels.items():
        try:
            control = page.get_by_label(label, exact=True)
            if control.count() == 0:
                errors.append(f"Target control not found: {label}")
                continue
            control.fill(str(mapped[field]))
        except Exception as error:
            errors.append(f"Could not fill {field}: {error}")
    image_files = mapped.get("image_files") or []
    if image_files:
        try:
            page.locator('input[type="file"]').set_input_files(image_files)
        except Exception as error:
            errors.append(f"Could not attach listing images: {error}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview one vehicle form mapping without submitting.")
    parser.add_argument("--input", type=Path, default=Path("data/vehicles.json"))
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    record = load_record(args.input, args.index)
    result = dry_run(record, {"country": ["South Africa"], "condition": ["Used"]})
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
