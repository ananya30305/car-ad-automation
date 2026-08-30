"""Download images for a vehicle listing."""

import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests

from car_ad_automation.core.config import DATA_DIR, IMAGE_DOWNLOAD_DIR

logger = logging.getLogger(__name__)


def download_vehicle_images(record: dict, session: requests.Session | None = None) -> list[str]:
    """
    Download images for a vehicle record.
    
    Args:
        record: Vehicle record containing source_id and image URLs
        session: Optional requests session for connection pooling
        
    Returns:
        List of local file paths for successfully downloaded images
        
    Raises:
        ValueError: If no images could be downloaded successfully
    """
    source_id = str(record.get("source_id") or record.get("id") or "").strip()
    image_urls = record.get("images") if isinstance(record.get("images"), list) else []
    
    if not source_id:
        logger.warning("No source_id found in record, cannot download images")
        return []
    
    if not image_urls:
        logger.warning("No image URLs found for source_id=%s", source_id)
        return []

    vehicle_dir = IMAGE_DOWNLOAD_DIR / source_id
    vehicle_dir.mkdir(parents=True, exist_ok=True)
    
    client = session or requests.Session()
    successful_paths: list[str] = []
    failed_count = 0
    
    for index, image_url in enumerate(image_urls, start=1):
        try:
            response = client.get(image_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            extension = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".jpg"
            if content_type and not content_type.startswith("image/"):
                logger.warning("Skipping non-image content for %s: %s", image_url, content_type)
                failed_count += 1
                continue
            destination = vehicle_dir / f"image_{index}{extension}"
            destination.write_bytes(response.content)
            successful_paths.append(str(destination))  # absolute path
        except requests.RequestException as error:
            logger.warning("Image download failed for %s: %s", image_url, error)
            failed_count += 1
            continue
    
    if failed_count:
        logger.warning("Downloaded %d/%d images for source_id=%s (%d failed)", 
                      len(successful_paths), len(successful_paths) + failed_count, source_id, failed_count)
    
    if not successful_paths:
        raise ValueError(f"All image downloads failed for source_id={source_id}")
    
    return successful_paths


def attach_downloaded_images(record: dict, session: requests.Session | None = None) -> dict:
    result = dict(record)
    result["image_files"] = download_vehicle_images(result, session)
    return result
