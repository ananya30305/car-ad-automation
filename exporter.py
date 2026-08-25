"""Export validated records for human-reviewed form workflows."""

import json
from pathlib import Path
from typing import Any


def form_record(car: dict[str, Any]) -> dict[str, Any]:
    result = dict(car)
    result.update({"category": "Vehicles", "subcategory": "Cars", "vehicle_type": "Used Cars", "country": "South Africa", "currency": "R (Rand)"})
    return result


def export_form_ready(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([form_record(record) for record in records], indent=2, ensure_ascii=False), encoding="utf-8")
