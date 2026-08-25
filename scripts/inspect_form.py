#!/usr/bin/env python3
"""Inspect the authenticated destination post form and dump selectors."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402


def main() -> int:
    config.ensure_directories()
    out_path = config.CONFIG_DIR / "form_map.inspected.json"
    print("Opening destination. Log in if prompted, open the full post-ad form,")
    print("select category Vehicles → Cars - Parts → Used cars in South Africa,")
    print("then return here and press ENTER.")
    print("URL:", config.DESTINATION_POST_URL)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.BROWSER_PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto(config.DESTINATION_POST_URL, wait_until="domcontentloaded")
        input("Press ENTER when the advertisement form is fully visible...")

        controls = []
        for locator in page.locator("input, textarea, select").all():
            try:
                controls.append(
                    {
                        "tag": locator.evaluate("el => el.tagName"),
                        "type": locator.get_attribute("type"),
                        "name": locator.get_attribute("name"),
                        "id": locator.get_attribute("id"),
                        "placeholder": locator.get_attribute("placeholder"),
                        "class": locator.get_attribute("class"),
                        "options": (
                            [
                                {
                                    "value": opt.get_attribute("value"),
                                    "text": opt.inner_text().strip(),
                                }
                                for opt in locator.locator("option").all()[:50]
                            ]
                            if locator.evaluate("el => el.tagName") == "SELECT"
                            else None
                        ),
                    }
                )
            except Exception as error:
                controls.append({"error": str(error)})

        payload = {
            "inspected_at": datetime.now(timezone.utc).isoformat(),
            "url": page.url,
            "title": page.title(),
            "controls": controls,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        html_path = config.REPORTS_DIR / "post_form_inspected.html"
        html_path.write_text(page.content(), encoding="utf-8")
        print(f"Wrote {out_path}")
        print(f"Wrote {html_path}")
        print("Merge confirmed selectors into config/form_map.json and set ready_for_browser=true")
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
