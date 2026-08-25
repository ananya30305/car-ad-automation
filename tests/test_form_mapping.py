"""Tests for form map loading and dropdown mapping behaviour."""

from __future__ import annotations

import json
from pathlib import Path

from app.posting.form_map import FormMapError, load_form_map, require_browser_ready
from app.validation.dropdowns import map_dropdown_value


def test_form_map_loads_and_has_inspected_extra_fields():
    form_map = load_form_map()
    assert "fields" in form_map
    assert form_map["fields"]["year"]["selector"] == "#exf_113"
    assert form_map["fields"]["fuel"]["name"] == "exf_116"
    assert form_map["category"]["path"][-1]["value"] == "35"
    assert form_map["images"]["file_input_name"] == "images"


def test_require_browser_ready_blocks_until_flag_set(tmp_path: Path, monkeypatch):
    path = tmp_path / "form_map.json"
    path.write_text(
        json.dumps(
            {
                "ready_for_browser": False,
                "fields": {},
                "core_fields_pending_login_inspection": {
                    "title": {"selector": None},
                    "description": {"selector": None},
                },
            }
        ),
        encoding="utf-8",
    )
    load_form_map.cache_clear()
    monkeypatch.setattr("app.posting.form_map.config.FORM_MAP_PATH", path)
    try:
        import pytest

        with pytest.raises(FormMapError):
            require_browser_ready()
    finally:
        load_form_map.cache_clear()


def test_passthrough_when_no_dropdown_map():
    mapped, error = map_dropdown_value("colour", "Black Sapphire Metal")
    assert error is None
    assert mapped == "Black Sapphire Metal"
