"""Validation for normalized vehicle records."""

from typing import Any
from models import Vehicle, ValidationResult


# Configuration
REQUIRED_FIELDS = ['title', 'price']
RECOMMENDED_FIELDS = ['year', 'mileage', 'fuel', 'transmission', 'contact_number', 'description', 'images']


def _is_valid_title(title: str) -> bool:
    """Validate title."""
    return bool(title and len(title) >= 3 and len(title) <= 200)


def _is_valid_price(price: int) -> bool:
    """Validate price is positive."""
    return price > 0


def _is_valid_year(year: int) -> bool:
    """Validate year is reasonable."""
    return 1900 <= year <= 2050


def _is_valid_mileage(mileage: int) -> bool:
    """Validate mileage is reasonable."""
    return 0 <= mileage <= 10_000_000


def _is_valid_seats(seats: int) -> bool:
    """Validate seat count."""
    return 1 <= seats <= 12


def validate_vehicle(vehicle: Vehicle) -> ValidationResult:
    """
    Validate a normalized vehicle record.
    
    Args:
        vehicle: Normalized Vehicle object
        
    Returns:
        ValidationResult with errors and quality score
    """
    errors = []
    warnings = []
    
    # Check required fields
    if not vehicle.title or not _is_valid_title(vehicle.title):
        errors.append("Title is missing or invalid (must be 3-200 chars)")
    
    if vehicle.price <= 0:
        errors.append("Price is missing or not positive")
    
    # Check optional but important fields
    if vehicle.year is not None and not _is_valid_year(vehicle.year):
        warnings.append(f"Year {vehicle.year} is outside normal range")
    
    if vehicle.mileage is not None and not _is_valid_mileage(vehicle.mileage):
        warnings.append(f"Mileage {vehicle.mileage} seems unrealistic")
    
    if vehicle.seats is not None and not _is_valid_seats(vehicle.seats):
        warnings.append(f"Seat count {vehicle.seats} is invalid")
    
    # Check images
    if not vehicle.images:
        warnings.append("No images provided")
    
    # Check description
    if not vehicle.description or len(vehicle.description) < 10:
        warnings.append("Description is missing or too short")
    
    # Check contact
    if not vehicle.contact_number:
        warnings.append("No contact number provided")
    
    # Calculate quality score based on filled fields
    total_fields = 12  # Count of fields to evaluate
    filled_fields = 0
    
    if vehicle.title:
        filled_fields += 1
    if vehicle.price > 0:
        filled_fields += 1
    if vehicle.year is not None:
        filled_fields += 1
    if vehicle.mileage is not None:
        filled_fields += 1
    if vehicle.fuel:
        filled_fields += 1
    if vehicle.transmission:
        filled_fields += 1
    if vehicle.colour:
        filled_fields += 1
    if vehicle.description:
        filled_fields += 1
    if vehicle.images:
        filled_fields += 1
    if vehicle.contact_number:
        filled_fields += 1
    if vehicle.dealer_name:
        filled_fields += 1
    if vehicle.location:
        filled_fields += 1
    
    quality_score = (filled_fields / total_fields) * 100
    
    # Determine validity: only required fields must be present
    is_valid = len(errors) == 0
    
    return ValidationResult(
        id=vehicle.id,
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        quality_score=round(quality_score, 2)
    )


def validate_records(vehicles: list[Vehicle]) -> tuple[list[Vehicle], list[ValidationResult]]:
    """
    Validate multiple records.
    
    Args:
        vehicles: List of Vehicle objects
        
    Returns:
        Tuple of (valid_vehicles, validation_results)
    """
    valid_vehicles = []
    validation_results = []
    
    for vehicle in vehicles:
        result = validate_vehicle(vehicle)
        validation_results.append(result)
        
        if result.valid:
            valid_vehicles.append(vehicle)
    
    return valid_vehicles, validation_results
