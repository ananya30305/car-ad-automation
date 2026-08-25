"""Playwright poster — posts only ready canonical records. No data inference."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import sync_playwright

from app import config
from app.canonical.models import CanonicalVehicle
from app.posting import form_filler
from app.posting.form_map import FormMapError, load_form_map, require_browser_ready

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_ready_records(path: Optional[Path] = None) -> list[CanonicalVehicle]:
    ready_path = path or (config.READY_DIR / "ready_to_post.json")
    if not ready_path.exists():
        return []
    data = json.loads(ready_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("ready_to_post.json must be a list")
    return [CanonicalVehicle.from_dict(item) for item in data if isinstance(item, dict)]


def post_vehicle(
    vehicle: CanonicalVehicle,
    *,
    dry_run: bool = True,
    headless: Optional[bool] = None,
) -> dict[str, Any]:
    """
    Open destination, fill using static form map, verify, optionally submit.

    Raises FormMapError if core selectors are not inspected yet.
    """
    config.ensure_directories()
    form_map = load_form_map()
    require_browser_ready(form_map)

    result: dict[str, Any] = {
        "id": vehicle.id,
        "status": "failed",
        "stage": "DRY_RUN" if dry_run else "POST",
        "error": None,
        "timestamp": _utc_now(),
        "dry_run": dry_run,
        "errors": [],
    }

    headless = config.HEADLESS if headless is None else headless

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.BROWSER_PROFILE_DIR),
            headless=headless,
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(config.PAGE_TIMEOUT_MS)
        try:
            page.goto(config.DESTINATION_POST_URL, wait_until="domcontentloaded")
            if "login" in page.url.casefold():
                result["error"] = (
                    "Destination requires login. Complete login in the browser profile, "
                    "then re-run."
                )
                result["errors"] = [result["error"]]
                context.close()
                return result

            errors = form_filler.select_category(page, form_map)
            # Extra fields load via AJAX after category selection
            page.wait_for_timeout(1500)
            errors.extend(form_filler.fill_mapped_fields(page, vehicle, form_map))
            errors.extend(form_filler.upload_images(page, vehicle, form_map))
            errors.extend(form_filler.verify_fields(page, vehicle, form_map))

            if errors:
                result["errors"] = errors
                result["error"] = "; ".join(errors)
                result["status"] = "failed"
            else:
                if dry_run:
                    result["status"] = "dry_run_passed"
                else:
                    submit = (form_map.get("core_fields_pending_login_inspection") or {}).get("submit") or {}
                    submit_selector = submit.get("selector")
                    if not submit_selector:
                        result["status"] = "failed"
                        result["error"] = "Submit selector not configured in form_map.json"
                        result["errors"] = [result["error"]]
                    else:
                        page.locator(submit_selector).first.click()
                        page.wait_for_timeout(2000)
                        result["status"] = "submitted"

            # Capture debug artifacts
            shot = config.REPORTS_DIR / f"{vehicle.id}_{'dryrun' if dry_run else 'post'}.png"
            page.screenshot(path=str(shot), full_page=True)
            result["screenshot"] = str(shot)
        except FormMapError:
            raise
        except Exception as error:
            result["status"] = "failed"
            result["error"] = str(error)
            result["errors"] = [str(error)]
            logger.exception("Posting failed for %s", vehicle.id)
        finally:
            context.close()

    result["timestamp"] = _utc_now()
    return result


def post_ready(
    *,
    vehicle_id: Optional[str] = None,
    dry_run: bool = True,
    limit: Optional[int] = None,
    headless: Optional[bool] = None,
) -> dict[str, Any]:
    records = load_ready_records()
    if vehicle_id:
        records = [r for r in records if r.id == str(vehicle_id)]
    limit = limit or config.MAX_ADS
    records = records[:limit]

    summary = {
        "ready": len(records),
        "dry_run_passed": 0,
        "dry_run_failed": 0,
        "submitted": 0,
        "failed": 0,
        "results": [],
        "blocked_reason": None,
    }

    if not records:
        summary["blocked_reason"] = "No ready records to post"
        return summary

    try:
        require_browser_ready()
    except FormMapError as error:
        summary["blocked_reason"] = str(error)
        for record in records:
            summary["results"].append(
                {
                    "id": record.id,
                    "status": "blocked",
                    "stage": "DRY_RUN" if dry_run else "POST",
                    "error": str(error),
                    "timestamp": _utc_now(),
                }
            )
            summary["failed"] += 1
        return summary

    for vehicle in records:
        outcome = post_vehicle(vehicle, dry_run=dry_run, headless=headless)
        summary["results"].append(outcome)
        if outcome["status"] == "dry_run_passed":
            summary["dry_run_passed"] += 1
        elif outcome["status"] == "submitted":
            summary["submitted"] += 1
        else:
            summary["failed"] += 1
            if dry_run:
                summary["dry_run_failed"] += 1

    report_path = config.REPORTS_DIR / f"post_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["report_path"] = str(report_path)
    return summary
