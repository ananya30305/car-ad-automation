"""Map source values to options exposed by a target form."""

from typing import Any


def normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def map_option(value: Any, available_options: list[str]) -> str | None:
    wanted = normalize(value)
    for option in available_options:
        if normalize(option) == wanted:
            return option
    return None


def map_vehicle(record: dict[str, Any], form_options: dict[str, list[str]]) -> tuple[dict[str, Any], list[str]]:
    mapped: dict[str, Any] = {}
    errors: list[str] = []
    for field in ("condition", "transmission", "fuel", "drive_type", "colour", "country"):
        value = record.get("location") if field == "country" else record.get(field)
        if value in (None, ""):
            errors.append(f"Missing source field: {field}")
            continue
        if field == "condition" and isinstance(value, str) and value.startswith("https://schema.org/"):
            value = value.rsplit("/", 1)[-1].replace("Condition", "")
        options = form_options.get(field)
        mapped_value = map_option(value, options) if options is not None else value
        if mapped_value is None:
            errors.append(f"No target option for {field}: {value}")
        else:
            mapped[field] = mapped_value
    for field in ("title", "description", "price", "mileage", "source_url"):
        if record.get(field) in (None, ""):
            errors.append(f"Missing source field: {field}")
        else:
            mapped[field] = record[field]
    mapped["images"] = list(record.get("images") or [])
    if len(mapped["images"]) != 5:
        errors.append("Exactly five listing images are required")
    return mapped, errors
