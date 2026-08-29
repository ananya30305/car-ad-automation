"""Download only images whose URL is associated with the current listing."""

import logging
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from car_ad_automation.core.config import DATA_DIR, REQUIRED_IMAGES

logger = logging.getLogger(__name__)


def download_vehicle_images(record: dict, session: requests.Session | None = None) -> list[str]:
    listing_id = str(record.get("listing_id") or "")
    image_urls = record.get("images") if isinstance(record.get("images"), list) else []
    if not listing_id:
        return []
    vehicle_dir = DATA_DIR / "vehicles" / listing_id
    vehicle_dir.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    local_paths: list[str] = []
    for index, image_url in enumerate(image_urls[:REQUIRED_IMAGES], start=1):
        if f"/{listing_id}/" not in image_url and f"/{listing_id}." not in image_url:
            continue
        try:
            response = client.get(image_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            extension = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".jpg"
            if content_type and not content_type.startswith("image/"):
                continue
            destination = vehicle_dir / f"image_{index}{extension}"
            destination.write_bytes(response.content)
            local_paths.append(str(destination.relative_to(DATA_DIR)))
        except requests.RequestException as error:
            logger.warning("Image download failed for %s: %s", image_url, error)
    return local_paths


def attach_downloaded_images(record: dict, session: requests.Session | None = None) -> dict:
    result = dict(record)
    result["image_files"] = download_vehicle_images(result, session)
    return result
