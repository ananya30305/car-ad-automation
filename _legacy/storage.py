"""Canonical dataset and validation-report storage."""

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def save_vehicle(record: dict[str, Any]) -> Path:
    listing_id = str(record.get("listing_id") or "unknown")
    destination = DATA_DIR / "vehicles" / listing_id / "vehicle.json"
    save_json(destination, record)
    return destination


def save_dataset(records: list[dict[str, Any]], validation_report: dict[str, Any]) -> None:
    save_json(DATA_DIR / "vehicles.json", records)
    save_json(DATA_DIR / "validation_report.json", validation_report)
