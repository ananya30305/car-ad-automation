"""Explicit dropdown / option value mapping. No fuzzy matching."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

from app import config


@lru_cache(maxsize=1)
def load_dropdown_map() -> dict[str, Any]:
    path = config.DROPDOWN_MAP_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def map_dropdown_value(field: str, value: Any) -> tuple[Optional[str], Optional[str]]:
    """
    Map a source value to a destination option.

    Returns (mapped_value, error).
    If the field has no dropdown map, returns (original, None) — text fields pass through.
    If the field has a map and value is unknown, returns (None, error).
    """
    dropdowns = load_dropdown_map()
    field_map = dropdowns.get(field)
    if not field_map:
        return (str(value) if value is not None else None), None

    options = field_map.get("options") or {}
    if not isinstance(options, dict):
        return None, f"Invalid dropdown map for {field}"

    raw = str(value).strip()
    # Exact key match first
    if raw in options:
        return options[raw], None

    # Case-insensitive key match only (still explicit keys, not fuzzy similarity)
    lowered = {str(k).casefold(): v for k, v in options.items()}
    if raw.casefold() in lowered:
        return lowered[raw.casefold()], None

    return None, f"No destination option for {field}: {value}"
