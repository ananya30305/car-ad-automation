"""Data normalization layer for vehicle records."""

import re
from typing import Any, Optional
from models import Vehicle


# Field mapping: alternative names -> canonical field
FIELD_MAPPING = {
    # ID fields
    'stock_id': 'id',
    'listing_id': 'id',
    'vehicle_id': 'id',
    'vin': 'id',
    
    # Title fields
    'listing_title': 'title',
    'vehicle_title': 'title',
    'name': 'title',
    
    # Price fields
    'selling_price': 'price',
    'asking_price': 'price',
    'list_price': 'price',
    'amount': 'price',
    
    # Year fields
    'vehicle_year': 'year',
    'manufacture_year': 'year',
    'model_year': 'year',
    'year_of_manufacture': 'year',
    'yom': 'year',
    
    # Mileage fields
    'kms': 'mileage',
    'kilometers': 'mileage',
    'odometer': 'mileage',
    'kilometers_driven': 'mileage',
    
    # Transmission fields
    'gearbox': 'transmission',
    'gearbox_type': 'transmission',
    
    # Fuel type
    'fuel_type': 'fuel',
    'engine_type': 'fuel',
    
    # Drive type
    'drivetrain': 'drive_type',
    'drive': 'drive_type',
    
    # Colour
    'color': 'colour',
    'paint_color': 'colour',
    'exterior_color': 'colour',
    
    # Contact
    'phone': 'contact_number',
    'mobile': 'contact_number',
    'dealer_phone': 'contact_number',
    'dealer_mobile': 'contact_number',
    'seller_phone': 'contact_number',
    'seller_mobile': 'contact_number',
    
    # Dealer
    'dealer': 'dealer_name',
    'seller_name': 'dealer_name',
    'seller': 'dealer_name',
    
    # Dealer address
    'seller_address': 'dealer_address',
    'seller_location': 'dealer_address',
    
    # Images
    'image_urls': 'images',
    'image_folder': 'images',
    'photo': 'images',
    'photos': 'images',
    'picture': 'images',
    'pictures': 'images',
    
    # Highlights
    'key_features': 'highlights',
    'selling_points': 'highlights',
    
    # Description
    'notes': 'description',
    'remarks': 'description',
    'comments': 'description',
    'details': 'description',
    'summary': 'description',
}


def normalize_field_name(field: str) -> str:
    """Map alternative field names to canonical names."""
    field_lower = field.lower().strip()
    return FIELD_MAPPING.get(field_lower, field_lower)


def normalize_price(value: Any) -> Optional[int]:
    """
    Normalize price to integer.
    
    Examples:
        "₹ 5,99,000" -> 599000
        "599000" -> 599000
        "599,000" -> 599000
        "$12,500" -> 12500
    """
    if value is None or value == "":
        return None
    
    # Convert to string
    price_str = str(value).strip()
    
    # Remove currency symbols and letters
    price_str = re.sub(r'[^\d.,]', '', price_str)
    
    # Handle different number formats
    # Remove thousands separators (comma or space)
    if ',' in price_str and '.' in price_str:
        # Determine which is thousands separator
        last_comma = price_str.rfind(',')
        last_dot = price_str.rfind('.')
        if last_dot > last_comma:
            # Use dot as decimal, remove commas
            price_str = price_str.replace(',', '')
        else:
            # Use comma as decimal, remove dots
            price_str = price_str.replace('.', '').replace(',', '.')
    elif ',' in price_str:
        # Check if it's a thousands separator or decimal
        parts = price_str.split(',')
        if len(parts[-1]) == 2:
            # Likely decimal separator
            price_str = price_str.replace(',', '.')
        else:
            # Likely thousands separator
            price_str = price_str.replace(',', '')
    
    try:
        price = float(price_str)
        return int(price)
    except (ValueError, AttributeError):
        return None


def normalize_mileage(value: Any) -> Optional[int]:
    """
    Normalize mileage to integer.
    
    Examples:
        "12,000 km" -> 12000
        "12 000 Km" -> 12000
        "12000" -> 12000
    """
    if value is None or value == "":
        return None
    
    # Convert to string
    mileage_str = str(value).strip()
    
    # Remove units (km, kms, miles, etc.)
    mileage_str = re.sub(r'\s*(km|kms|miles|mi|m)s?$', '', mileage_str, flags=re.I)
    
    # Remove any non-digit characters except decimal point
    mileage_str = re.sub(r'[^\d.]', '', mileage_str)
    
    try:
        mileage = float(mileage_str)
        return int(mileage)
    except (ValueError, AttributeError):
        return None


def normalize_year(value: Any) -> Optional[int]:
    """
    Normalize year to integer.
    
    Examples:
        "2025" -> 2025
        2025 -> 2025
    """
    if value is None or value == "":
        return None
    
    try:
        year = int(str(value).strip())
        # Validate year is reasonable (1900-2050)
        if 1900 <= year <= 2050:
            return year
        return None
    except (ValueError, AttributeError):
        return None


def normalize_string(value: Any) -> Optional[str]:
    """
    Normalize string: trim, remove extra spaces, handle unicode.
    """
    if value is None or value == "":
        return None
    
    # Convert to string
    text = str(value).strip()
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Return None if empty
    return text if text else None


def normalize_seats(value: Any) -> Optional[int]:
    """Normalize seat count."""
    if value is None or value == "":
        return None
    
    # Extract just the number
    match = re.search(r'(\d+)', str(value))
    if match:
        seats = int(match.group(1))
        if 1 <= seats <= 12:
            return seats
    return None


def normalize_list(value: Any) -> list[str]:
    """
    Normalize list of strings.
    
    Handles:
        ["feature1", "feature2"] -> ["feature1", "feature2"]
        "feature1, feature2" -> ["feature1", "feature2"]
        "feature1; feature2" -> ["feature1", "feature2"]
    """
    if value is None:
        return []
    
    if isinstance(value, list):
        # Filter and normalize each item
        return [s.strip() for s in value if isinstance(s, str) and s.strip()]
    
    if isinstance(value, str):
        # Split by common delimiters
        items = re.split(r'[,;]', value)
        return [s.strip() for s in items if s.strip()]
    
    return []


def normalize_phone(value: Any) -> Optional[str]:
    """
    Normalize phone number.
    Preserves source format - does NOT generate missing numbers.
    """
    if value is None or value == "":
        return None
    
    phone_str = str(value).strip()
    
    # Remove any non-numeric characters except leading +
    if phone_str.startswith('+'):
        phone_str = '+' + re.sub(r'[^\d]', '', phone_str[1:])
    else:
        phone_str = re.sub(r'[^\d]', '', phone_str)
    
    # Basic validation: should have at least 7 digits
    digits = re.sub(r'[^\d]', '', phone_str)
    if len(digits) < 7:
        return None
    
    return phone_str if phone_str else None


def normalize_images(value: Any) -> list[str]:
    """
    Normalize image list.
    
    Handles:
        ["path1.jpg", "path2.jpg"] -> ["path1.jpg", "path2.jpg"]
        {"folder": "images/123"} -> images from folder
        "path1.jpg, path2.jpg" -> ["path1.jpg", "path2.jpg"]
    """
    if value is None:
        return []
    
    if isinstance(value, list):
        # Flatten and normalize
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item.strip())
            elif isinstance(item, dict) and 'folder' in item:
                # Will be handled by image manager
                result.append(f"folder:{item['folder']}")
        return [img for img in result if img]
    
    if isinstance(value, str):
        # Split by comma
        items = [s.strip() for s in value.split(',') if s.strip()]
        return items
    
    if isinstance(value, dict):
        if 'folder' in value:
            return [f"folder:{value['folder']}"]
        if 'images' in value:
            return normalize_images(value['images'])
    
    return []


def normalize_record(record: dict[str, Any]) -> Vehicle:
    """
    Normalize a raw record into a Vehicle object.
    
    Args:
        record: Raw input record with possibly alternative field names
        
    Returns:
        Normalized Vehicle object
    """
    # First, normalize all field names
    normalized = {}
    for key, value in record.items():
        canonical_name = normalize_field_name(key)
        # Keep original value for now
        normalized[canonical_name] = value
    
    # Extract and normalize each field
    vehicle = Vehicle(
        id=normalize_string(normalized.get('id')) or f"auto_{id(record)}",
        title=normalize_string(normalized.get('title')) or "Untitled",
        price=normalize_price(normalized.get('price')) or 0,
        condition=normalize_string(normalized.get('condition', 'used')) or 'used',
        year=normalize_year(normalized.get('year')),
        mileage=normalize_mileage(normalized.get('mileage')),
        transmission=normalize_string(normalized.get('transmission')),
        fuel=normalize_string(normalized.get('fuel')),
        drive_type=normalize_string(normalized.get('drive_type')),
        colour=normalize_string(normalized.get('colour')),
        seats=normalize_seats(normalized.get('seats')),
        description=normalize_string(normalized.get('description')),
        dealer_name=normalize_string(normalized.get('dealer_name')),
        dealer_address=normalize_string(normalized.get('dealer_address')),
        contact_number=normalize_phone(normalized.get('contact_number')),
        location=normalize_string(normalized.get('location')),
        features=normalize_list(normalized.get('features')),
        highlights=normalize_list(normalized.get('highlights')),
        images=normalize_images(normalized.get('images')),
        currency=normalize_string(normalized.get('currency', 'ZAR')) or 'ZAR',
        source_id=normalize_string(normalized.get('source_id')),
    )
    
    return vehicle
