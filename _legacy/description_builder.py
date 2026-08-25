"""Generate descriptions from vehicle fields when needed."""

from models import Vehicle


def build_description(vehicle: Vehicle) -> str:
    """
    Build a factual description from vehicle fields.
    
    Only includes fields that actually exist.
    Never invents specifications.
    
    Args:
        vehicle: Vehicle object
        
    Returns:
        Generated description string
    """
    if vehicle.description:
        # If description already supplied, preserve it
        return vehicle.description
    
    # Build from structured fields
    lines = []
    
    # Title/Vehicle name
    if vehicle.title:
        lines.append(f"Vehicle: {vehicle.title}")
    
    # Year
    if vehicle.year:
        lines.append(f"Year: {vehicle.year}")
    
    # Condition
    if vehicle.condition:
        lines.append(f"Condition: {vehicle.condition.title()}")
    
    # Mileage
    if vehicle.mileage is not None:
        lines.append(f"Mileage: {vehicle.mileage:,} km")
    
    # Transmission
    if vehicle.transmission:
        lines.append(f"Transmission: {vehicle.transmission.title()}")
    
    # Fuel
    if vehicle.fuel:
        lines.append(f"Fuel: {vehicle.fuel.title()}")
    
    # Drive type
    if vehicle.drive_type:
        lines.append(f"Drive Type: {vehicle.drive_type.upper()}")
    
    # Colour
    if vehicle.colour:
        lines.append(f"Colour: {vehicle.colour}")
    
    # Seats
    if vehicle.seats:
        lines.append(f"Seats: {vehicle.seats}")
    
    # Price
    if vehicle.price:
        lines.append(f"Price: {vehicle.currency} {vehicle.price:,}")
    
    # Features
    if vehicle.features:
        features_text = ", ".join(vehicle.features[:5])  # Limit to first 5
        lines.append(f"Features: {features_text}")
    
    # Highlights
    if vehicle.highlights:
        highlights_text = ", ".join(vehicle.highlights[:3])  # Limit to first 3
        lines.append(f"Highlights: {highlights_text}")
    
    # Location
    if vehicle.location:
        lines.append(f"Location: {vehicle.location}")
    
    # Contact
    if vehicle.contact_number:
        lines.append(f"Contact: {vehicle.contact_number}")
    
    # Dealer
    if vehicle.dealer_name:
        lines.append(f"Dealer: {vehicle.dealer_name}")
    
    description = "\n".join(lines)
    
    # Ensure minimum length
    if description:
        return description
    
    # Fallback if nothing was added
    return vehicle.title or "Vehicle Advertisement"


def ensure_description(vehicle: Vehicle) -> Vehicle:
    """
    Ensure vehicle has a description.
    
    If missing, generates one. If present, preserves it.
    
    Args:
        vehicle: Vehicle object
        
    Returns:
        Vehicle object with description guaranteed
    """
    if not vehicle.description or len(vehicle.description) < 10:
        vehicle.description = build_description(vehicle)
    
    return vehicle
