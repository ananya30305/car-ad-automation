"""Load raw source records from vehicle folders, HTML, or inventory files."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Optional

from app import config
from app.canonical.extractor import parse_listing_html

logger = logging.getLogger(__name__)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vehicle_folder(folder: Path) -> Optional[dict[str, Any]]:
    vehicle_json = folder / "vehicle.json"
    if not vehicle_json.exists():
        return None
    data = _read_json(vehicle_json)
    if not isinstance(data, dict):
        raise ValueError(f"{vehicle_json} must contain a JSON object")
    data.setdefault("listing_id", folder.name)
    data.setdefault("id", data.get("listing_id") or folder.name)

    # Optional raw HTML alongside the folder / in data/raw
    html_candidates = [
        folder / "source.html",
        folder / "page.html",
        config.RAW_DIR / f"{folder.name}.html",
    ]
    for html_path in html_candidates:
        if html_path.exists():
            source_url = data.get("source_url") or f"https://www.cars.co.za/{folder.name}/"
            parsed = parse_listing_html(html_path.read_text(encoding="utf-8", errors="replace"), source_url)
            # Structured parse wins over nulls; keep existing non-null values
            for key, value in parsed.items():
                if value in (None, "", [], {}):
                    continue
                current = data.get(key)
                if current in (None, "", [], {}):
                    data[key] = value
            break
    return data


def load_all_vehicle_folders(vehicle_id: Optional[str] = None) -> list[dict[str, Any]]:
    config.ensure_directories()
    if not config.VEHICLES_DIR.exists():
        return []
    records: list[dict[str, Any]] = []
    folders = sorted(p for p in config.VEHICLES_DIR.iterdir() if p.is_dir())
    for folder in folders:
        if vehicle_id and folder.name != str(vehicle_id):
            continue
        record = load_vehicle_folder(folder)
        if record:
            records.append(record)
    return records


def load_inventory_json(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data, dict):
        data = data.get("vehicles") or data.get("items") or [data]
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list of vehicle objects")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        item = dict(item)
        item.setdefault("id", item.get("listing_id") or item.get("stock_id") or f"inv_{index}")
        records.append(item)
    return records


def load_inventory_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records: list[dict[str, Any]] = []
        for index, row in enumerate(reader):
            item = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            # Split list-like columns
            for key in ("features", "highlights", "images"):
                if key in item and isinstance(item[key], str) and item[key]:
                    item[key] = [part.strip() for part in item[key].split("|") if part.strip()]
            item.setdefault("id", item.get("listing_id") or item.get("stock_id") or f"csv_{index}")
            records.append(item)
        return records


def load_sources(vehicle_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Preferred order:
    1) data/vehicles/*/vehicle.json (+ optional raw HTML)
    2) data/inventory.json
    3) data/inventory.csv
    """
    config.ensure_directories()
    records = load_all_vehicle_folders(vehicle_id=vehicle_id)
    if records:
        logger.info("Loaded %d records from %s", len(records), config.VEHICLES_DIR)
        return records

    if config.INVENTORY_JSON.exists():
        records = load_inventory_json(config.INVENTORY_JSON)
        if vehicle_id:
            records = [r for r in records if str(r.get("id")) == str(vehicle_id)]
        logger.info("Loaded %d records from %s", len(records), config.INVENTORY_JSON)
        return records

    if config.INVENTORY_CSV.exists():
        records = load_inventory_csv(config.INVENTORY_CSV)
        if vehicle_id:
            records = [r for r in records if str(r.get("id")) == str(vehicle_id)]
        logger.info("Loaded %d records from %s", len(records), config.INVENTORY_CSV)
        return records

    logger.warning("No source data found under %s or inventory files", config.VEHICLES_DIR)
    return []
