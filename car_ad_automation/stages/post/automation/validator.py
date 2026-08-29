"""Dry-run form validation; no submission is implemented here."""

from typing import Any


def validate_form_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("source_url", "title", "description", "price"):
        if record.get(field) in (None, ""):
            errors.append(f"Missing form field: {field}")
    images = record.get("images")
    if not isinstance(images, list) or len(images) != 5 or len(set(images)) != 5:
        errors.append("Form requires five unique images")
    return errors
