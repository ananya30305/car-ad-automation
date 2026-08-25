"""Single production pipeline: ingest → canonicalize → preflight → post."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app import config
from app.canonical.images import prepare_images
from app.canonical.models import CanonicalVehicle, ProcessingRecord, StageResult
from app.canonical.normalizer import canonicalize_record
from app.ingest.source_reader import load_sources
from app.posting.poster import post_ready
from app.validation.preflight import validate_vehicle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def prepare(
    vehicle_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Run ingest → canonicalize → image prep → preflight. Never opens the browser."""
    config.ensure_directories()
    raw_records = load_sources(vehicle_id=vehicle_id)
    if limit is not None:
        raw_records = raw_records[:limit]

    ready: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    canonical_all: list[dict[str, Any]] = []
    processing: list[dict[str, Any]] = []

    for raw in raw_records:
        record_id = str(raw.get("id") or raw.get("listing_id") or "unknown")
        proc = ProcessingRecord(id=record_id, status="ok", stage="INGEST")
        proc.add(StageResult(id=record_id, stage="INGEST", status="ok"))

        try:
            vehicle = canonicalize_record(raw)
            proc.add(StageResult(id=vehicle.id, stage="CANONICALIZE", status="ok"))
        except Exception as error:
            proc.add(
                StageResult(
                    id=record_id,
                    stage="CANONICALIZE",
                    status="failed",
                    error=str(error),
                )
            )
            rejected.append({"id": record_id, "errors": [f"canonicalize failed: {error}"], "stage": "CANONICALIZE"})
            processing.append(proc.to_dict())
            logger.error("[%s] canonicalize failed: %s", record_id, error)
            continue

        image_urls = []
        if isinstance(raw.get("images"), list):
            image_urls.extend(raw["images"])
        _, image_errors = prepare_images(vehicle, image_urls=image_urls)
        if image_errors:
            proc.add(
                StageResult(
                    id=vehicle.id,
                    stage="CANONICALIZE",
                    status="failed",
                    error="; ".join(image_errors),
                    details={"images": vehicle.images},
                )
            )
        else:
            proc.add(
                StageResult(
                    id=vehicle.id,
                    stage="CANONICALIZE",
                    status="ok",
                    details={"images": len(vehicle.images)},
                )
            )

        canonical_all.append(vehicle.to_dict())
        _write_json(config.CANONICAL_DIR / f"{vehicle.id}.json", vehicle.to_dict())

        result = validate_vehicle(vehicle)
        if image_errors:
            # Ensure image failures are part of rejection even if validate also catches them
            for err in image_errors:
                if err not in result.errors:
                    result.errors.append(err)
            result.valid = False

        if result.valid:
            ready.append(vehicle.to_dict())
            proc.add(StageResult(id=vehicle.id, stage="VALIDATE", status="ok"))
            logger.info("[READY] %s | %s", vehicle.id, vehicle.title)
        else:
            rejected.append(
                {
                    "id": vehicle.id,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "stage": "VALIDATE",
                    "title": vehicle.title,
                }
            )
            proc.add(
                StageResult(
                    id=vehicle.id,
                    stage="VALIDATE",
                    status="rejected",
                    error="; ".join(result.errors),
                )
            )
            logger.warning("[REJECTED] %s | %s", vehicle.id, "; ".join(result.errors))

        processing.append(proc.to_dict())

    _write_json(config.READY_DIR / "ready_to_post.json", ready)
    _write_json(config.REJECTED_DIR / "rejected.json", rejected)
    _write_json(config.CANONICAL_DIR / "all.json", canonical_all)
    report = {
        "timestamp": _utc_now(),
        "input": len(raw_records),
        "ready": len(ready),
        "rejected": len(rejected),
        "processing": processing,
    }
    _write_json(config.REPORTS_DIR / "prepare_report.json", report)
    return report


def run_pipeline(
    *,
    vehicle_id: Optional[str] = None,
    batch: bool = False,
    dry_run: bool = True,
    prepare_only: bool = False,
    validate_only: bool = False,
    limit: Optional[int] = None,
    headless: Optional[bool] = None,
) -> dict[str, Any]:
    if not batch and vehicle_id is None and not prepare_only and not validate_only:
        # Default to prepare-only summary when no mode flags — safety
        prepare_only = True

    if batch and vehicle_id:
        raise SystemExit("Use either --id or --batch, not both")

    effective_limit = 1 if vehicle_id else (limit or config.MAX_ADS)
    if vehicle_id:
        effective_limit = 1

    prepare_report = prepare(vehicle_id=vehicle_id, limit=None if vehicle_id else effective_limit)

    summary: dict[str, Any] = {
        "READY": prepare_report["ready"],
        "REJECTED": prepare_report["rejected"],
        "DRY-RUN PASSED": 0,
        "DRY-RUN FAILED": 0,
        "SUBMITTED": 0,
        "FAILED": 0,
        "blocked_reason": None,
    }

    if prepare_only or validate_only:
        _print_summary(summary)
        return {"prepare": prepare_report, "summary": summary}

    post_summary = post_ready(
        vehicle_id=vehicle_id,
        dry_run=dry_run,
        limit=effective_limit,
        headless=headless,
    )
    summary["DRY-RUN PASSED"] = post_summary.get("dry_run_passed", 0)
    summary["DRY-RUN FAILED"] = post_summary.get("dry_run_failed", 0)
    summary["SUBMITTED"] = post_summary.get("submitted", 0)
    summary["FAILED"] = post_summary.get("failed", 0)
    summary["blocked_reason"] = post_summary.get("blocked_reason")
    _print_summary(summary)
    if summary["blocked_reason"]:
        logger.error("Posting blocked: %s", summary["blocked_reason"])
    return {"prepare": prepare_report, "post": post_summary, "summary": summary}


def _print_summary(summary: dict[str, Any]) -> None:
    print()
    print("=" * 60)
    for key in ("READY", "REJECTED", "DRY-RUN PASSED", "DRY-RUN FAILED", "SUBMITTED", "FAILED"):
        if key in summary:
            print(f"{key}: {summary[key]}")
    if summary.get("blocked_reason"):
        print(f"BLOCKED: {summary['blocked_reason']}")
    print("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.pipeline",
        description="Vehicle ad automation pipeline",
    )
    parser.add_argument("--id", dest="vehicle_id", help="Process a single vehicle id")
    parser.add_argument("--batch", action="store_true", help="Process up to MAX_ADS ready vehicles")
    parser.add_argument("--dry-run", action="store_true", help="Fill/verify form without submitting")
    parser.add_argument("--submit", action="store_true", help="Allow live submission (not dry-run)")
    parser.add_argument("--prepare", action="store_true", help="Only ingest/canonicalize/validate")
    parser.add_argument("--validate", action="store_true", help="Alias for --prepare")
    parser.add_argument("--limit", type=int, default=None, help="Max records to prepare/post")
    parser.add_argument("--headless", action="store_true", help="Force headless browser")
    parser.add_argument("--headed", action="store_true", help="Force headed browser")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dry_run = True
    if args.submit:
        dry_run = False
    if args.dry_run:
        dry_run = True

    headless = None
    if args.headless:
        headless = True
    if args.headed:
        headless = False

    # If user asks for dry-run/submit/batch/id without prepare-only, run full path
    prepare_only = args.prepare or args.validate
    if args.dry_run or args.submit or args.batch or args.vehicle_id:
        if not (args.prepare or args.validate):
            prepare_only = False

    run_pipeline(
        vehicle_id=args.vehicle_id,
        batch=args.batch,
        dry_run=dry_run,
        prepare_only=prepare_only or not (args.dry_run or args.submit or args.batch or args.vehicle_id),
        validate_only=args.validate,
        limit=args.limit,
        headless=headless,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
