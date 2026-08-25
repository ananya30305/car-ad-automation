"""Load and validate the static destination form map."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app import config


class FormMapError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_form_map(path: str | None = None) -> dict[str, Any]:
    map_path = Path(path) if path else config.FORM_MAP_PATH
    if not map_path.exists():
        raise FormMapError(f"Form map not found: {map_path}")
    data = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FormMapError("form_map.json must be a JSON object")
    return data


def require_browser_ready(form_map: dict[str, Any] | None = None) -> dict[str, Any]:
    form_map = form_map or load_form_map()
    if form_map.get("ready_for_browser") is True:
        return form_map

    pending = form_map.get("core_fields_pending_login_inspection") or {}
    missing = [
        name
        for name, spec in pending.items()
        if name != "submit" and not (isinstance(spec, dict) and spec.get("selector"))
    ]
    raise FormMapError(
        "Destination core form fields are not fully inspected yet "
        f"(missing selectors for: {', '.join(missing) or 'unknown'}). "
        "Log in and run ./run.sh inspect to capture selectors, then set "
        "ready_for_browser=true in config/form_map.json. "
        "Category extra-field selectors (exf_*) are already available from AJAX inspection."
    )


def field_specs(form_map: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    form_map = form_map or load_form_map()
    fields = dict(form_map.get("fields") or {})
    pending = form_map.get("core_fields_pending_login_inspection") or {}
    for name, spec in pending.items():
        if isinstance(spec, dict) and spec.get("selector"):
            fields[name] = spec
    return fields
