"""Duplicate detection using fingerprinting."""

import hashlib
from typing import Optional
from models import Vehicle, DuplicateCheckResult


def generate_fingerprint(vehicle: Vehicle) -> str:
    """
    Generate a deterministic fingerprint for a vehicle.
    
    Combines: normalized title, year, price, and condition
    to create a unique hash.
    """
    components = [
        vehicle.id,
        vehicle.title.lower().strip(),
        str(vehicle.year or ""),
        str(vehicle.price or ""),
        vehicle.condition.lower().strip(),
    ]
    
    fingerprint_str = "|".join(components)
    fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    return fingerprint


def check_duplicate(
    vehicle: Vehicle, 
    processed_fingerprints: set[str]
) -> DuplicateCheckResult:
    """
    Check if vehicle is a duplicate.
    
    Args:
        vehicle: Vehicle to check
        processed_fingerprints: Set of previously seen fingerprints
        
    Returns:
        DuplicateCheckResult
    """
    fingerprint = generate_fingerprint(vehicle)
    
    is_duplicate = fingerprint in processed_fingerprints
    
    return DuplicateCheckResult(
        id=vehicle.id,
        is_duplicate=is_duplicate,
        fingerprint=fingerprint,
        reason="Matching ID, title, year, price, and condition" if is_duplicate else None
    )


def check_duplicates(
    vehicles: list[Vehicle],
    processed_fingerprints: Optional[set[str]] = None
) -> tuple[list[Vehicle], list[DuplicateCheckResult], set[str]]:
    """
    Check multiple vehicles for duplicates.
    
    Args:
        vehicles: List of vehicles to check
        processed_fingerprints: Set of previously processed fingerprints
        
    Returns:
        Tuple of (unique_vehicles, duplicate_results, updated_fingerprints)
    """
    if processed_fingerprints is None:
        processed_fingerprints = set()
    
    unique_vehicles = []
    duplicate_results = []
    fingerprints = processed_fingerprints.copy()
    
    for vehicle in vehicles:
        result = check_duplicate(vehicle, fingerprints)
        
        if result.is_duplicate:
            duplicate_results.append(result)
        else:
            unique_vehicles.append(vehicle)
            fingerprints.add(result.fingerprint)
    
    return unique_vehicles, duplicate_results, fingerprints
