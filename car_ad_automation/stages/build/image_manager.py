"""Image validation and management."""

import os
from pathlib import Path
from typing import Optional, Callable
from car_ad_automation.core.models import Vehicle


SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
IMAGE_LIMIT = 10


def is_valid_image_path(path: str) -> bool:
    """
    Check if image path is valid local file.
    
    Args:
        path: File path
        
    Returns:
        True if file exists and is supported format
    """
    try:
        file_path = Path(path)
        
        # Check file exists
        if not file_path.exists():
            return False
        
        # Check is file (not directory)
        if not file_path.is_file():
            return False
        
        # Check file size
        if file_path.stat().st_size > MAX_IMAGE_SIZE:
            return False
        
        # Check format
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            return False
        
        return True
    except (OSError, ValueError):
        return False


def is_valid_image_url(url: str) -> bool:
    """
    Check if URL is valid image URL.
    
    Args:
        url: Image URL
        
    Returns:
        True if URL appears to be image
    """
    # Basic check: starts with http/https and has valid extension
    if not url.lower().startswith(('http://', 'https://')):
        return False
    
    # Extract file extension
    try:
        # Remove query params
        path = url.split('?')[0]
        
        # Check extension
        if not any(path.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
            return False
        
        # Avoid known placeholder/placeholder URLs
        if any(skip in url.lower() for skip in ('placeholder', 'logo', 'sprite', 'icon', 'fallback')):
            return False
        
        return True
    except Exception:
        return False


def validate_images(image_paths: list[str], base_dir: Optional[Path] = None) -> tuple[list[str], list[str]]:
    """
    Validate list of images.
    
    Args:
        image_paths: List of image paths/URLs
        base_dir: Base directory for relative paths
        
    Returns:
        Tuple of (valid_images, invalid_reasons)
    """
    valid_images = []
    invalid_reasons = []
    
    for idx, image in enumerate(image_paths):
        if not image or not isinstance(image, str):
            invalid_reasons.append(f"Image {idx}: Invalid path (empty or not string)")
            continue
        
        # Handle folder notation
        if image.startswith('folder:'):
            folder_path = image.split(':', 1)[1]
            # We'll handle this in image discovery
            valid_images.append(image)
            continue
        
        # Check if URL
        if image.lower().startswith(('http://', 'https://')):
            if is_valid_image_url(image):
                valid_images.append(image)
            else:
                invalid_reasons.append(f"Image {idx}: Invalid URL format or placeholder")
        else:
            # Local file
            image_path = Path(image) if not base_dir else (base_dir / image)
            
            if is_valid_image_path(str(image_path)):
                valid_images.append(str(image_path))
            else:
                invalid_reasons.append(f"Image {idx}: File not found or unsupported format ({image})")
    
    return valid_images[:IMAGE_LIMIT], invalid_reasons


def discover_images_in_folder(folder_path: str) -> list[str]:
    """
    Discover all images in a folder.
    
    Args:
        folder_path: Path to folder
        
    Returns:
        List of image paths
    """
    images = []
    
    try:
        folder = Path(folder_path)
        
        if not folder.exists() or not folder.is_dir():
            return images
        
        # Find all images in folder
        for ext in SUPPORTED_FORMATS:
            images.extend([
                str(p) for p in folder.glob(f'*{ext}')
                if p.is_file() and p.stat().st_size < MAX_IMAGE_SIZE
            ])
        
        # Also check case-insensitive
        for ext in SUPPORTED_FORMATS:
            images.extend([
                str(p) for p in folder.glob(f'*{ext.upper()}')
                if p.is_file() and p.stat().st_size < MAX_IMAGE_SIZE
            ])
        
        # Remove duplicates and limit
        images = list(dict.fromkeys(images))
        return images[:IMAGE_LIMIT]
    
    except (OSError, ValueError):
        return images


def resolve_images(images: list[str], base_dir: Optional[Path] = None) -> tuple[list[str], list[str]]:
    """
    Resolve images: expand folders, validate paths.
    
    Args:
        images: List of image paths (may include folder notation)
        base_dir: Base directory for relative paths
        
    Returns:
        Tuple of (resolved_images, errors)
    """
    resolved = []
    errors = []
    
    for image in images:
        if image.startswith('folder:'):
            # Extract and discover folder contents
            folder_path = image.split(':', 1)[1]
            
            if not base_dir:
                folder_full = Path(folder_path)
            else:
                folder_full = base_dir / folder_path
            
            discovered = discover_images_in_folder(str(folder_full))
            
            if not discovered:
                errors.append(f"No images found in folder: {folder_path}")
            else:
                resolved.extend(discovered)
        else:
            resolved.append(image)
    
    # Validate and return
    return validate_images(resolved, base_dir)


def validate_vehicle_images(vehicle: Vehicle, base_dir: Optional[Path] = None) -> tuple[list[str], list[str]]:
    """
    Validate images for a vehicle.
    
    Args:
        vehicle: Vehicle object
        base_dir: Base directory for relative paths
        
    Returns:
        Tuple of (valid_images, errors)
    """
    if not vehicle.images:
        return [], []
    
    valid, errors = resolve_images(vehicle.images, base_dir)
    
    return valid, errors
