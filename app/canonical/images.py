"""Download and prepare exactly REQUIRED_IMAGES local image files."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from app import config
from app.canonical.models import CanonicalVehicle

logger = logging.getLogger(__name__)

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _is_valid_image_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.casefold() not in SUPPORTED:
        return False
    if path.stat().st_size <= 0:
        return False
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def _discover_local_images(vehicle_id: str) -> list[Path]:
    candidates: list[Path] = []
    search_dirs = [
        config.IMAGE_DIR / vehicle_id,
        config.VEHICLES_DIR / vehicle_id,
        config.DATA_DIR / "vehicles" / vehicle_id,
    ]
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.casefold() in SUPPORTED:
                candidates.append(path)
    # Deduplicate by resolved path
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _download_url(url: str, destination: Path, session: requests.Session) -> Optional[Path]:
    try:
        response = session.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type and not content_type.startswith("image/"):
            logger.warning("Skipping non-image URL %s (%s)", url, content_type)
            return None
        extension = (
            mimetypes.guess_extension(content_type)
            or Path(urlparse(url).path).suffix
            or ".jpg"
        )
        if extension.casefold() == ".jpe":
            extension = ".jpg"
        path = destination.with_suffix(extension)
        path.write_bytes(response.content)
        if not _is_valid_image_file(path):
            path.unlink(missing_ok=True)
            return None
        return path
    except requests.RequestException as error:
        logger.warning("Image download failed for %s: %s", url, error)
        return None


def prepare_images(
    vehicle: CanonicalVehicle,
    image_urls: Optional[list[str]] = None,
    session: Optional[requests.Session] = None,
) -> tuple[list[str], list[str]]:
    """
    Prepare local images for a vehicle.

    Returns (local_paths, errors).
    Does not duplicate the same image to pad to five.
    """
    errors: list[str] = []
    target_dir = config.IMAGE_DIR / vehicle.id
    target_dir.mkdir(parents=True, exist_ok=True)

    usable: list[Path] = []
    seen_bytes: set[int] = set()

    def _add(path: Path) -> None:
        if not _is_valid_image_file(path):
            return
        size = path.stat().st_size
        # Reject exact byte-size duplicates as a simple duplicate guard
        if size in seen_bytes and size > 0:
            # Also compare content hash lightly via size+name; skip clear copies later
            for existing in usable:
                if existing.stat().st_size == size and existing.read_bytes() == path.read_bytes():
                    return
        seen_bytes.add(size)
        # Copy into IMAGE_DIR if needed
        dest = target_dir / f"image_{len(usable) + 1}{path.suffix.casefold()}"
        if path.resolve() != dest.resolve():
            dest.write_bytes(path.read_bytes())
            path = dest
        usable.append(path)

    for local in _discover_local_images(vehicle.id):
        _add(local)
        if len(usable) >= config.REQUIRED_IMAGES:
            break

    urls = [u for u in (image_urls or []) if isinstance(u, str) and u.startswith("http")]
    client = session or requests.Session()
    client.headers.setdefault("User-Agent", config.USER_AGENT)

    for index, url in enumerate(urls, start=1):
        if len(usable) >= config.REQUIRED_IMAGES:
            break
        # Prefer listing-scoped URLs when id is present in path
        if vehicle.id and f"/{vehicle.id}/" not in url and f"/{vehicle.id}." not in url:
            # Still allow og images that include the id elsewhere
            if vehicle.id not in url:
                continue
        temp = target_dir / f"download_{index}"
        downloaded = _download_url(url, temp, client)
        if downloaded:
            _add(downloaded)

    if len(usable) < config.REQUIRED_IMAGES:
        errors.append(
            f"only {len(usable)} usable images found (requires exactly {config.REQUIRED_IMAGES})"
        )
        vehicle.images = [str(path) for path in usable]
        return vehicle.images, errors

    if len(usable) > config.REQUIRED_IMAGES:
        usable = usable[: config.REQUIRED_IMAGES]

    # Exactly REQUIRED_IMAGES
    vehicle.images = [str(path.resolve()) for path in usable]
    return vehicle.images, errors
