#!/usr/bin/env python3
"""Inspect a source vehicle folder / HTML and print extracted canonical fields."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.canonical.images import prepare_images  # noqa: E402
from app.canonical.normalizer import canonicalize_record  # noqa: E402
from app.ingest.source_reader import load_sources  # noqa: E402
from app.validation.preflight import validate_vehicle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Vehicle listing id")
    args = parser.parse_args()
    records = load_sources(vehicle_id=args.id)
    if not records:
        print(f"No source found for id={args.id}")
        return 1
    raw = records[0]
    vehicle = canonicalize_record(raw)
    urls = raw.get("images") if isinstance(raw.get("images"), list) else []
    prepare_images(vehicle, image_urls=urls)
    result = validate_vehicle(vehicle)
    print(json.dumps({"canonical": vehicle.to_dict(), "preflight": result.to_dict()}, indent=2))
    return 0 if result.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
