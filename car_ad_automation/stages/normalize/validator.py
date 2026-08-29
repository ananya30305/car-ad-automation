"""Validation for normalized vehicle records.

Validates Vehicle objects before they enter the advertisement
processing and submission pipeline.
"""

from typing import Any

from car_ad_automation.core.models import Vehicle, ValidationResult


# ============================================================
# CONFIGURATION
# ============================================================

# Fields that must be present for a vehicle to be considered valid.
REQUIRED_FIELDS = [
    "title",
    "price",
]

# Fields that improve advertisement quality.
RECOMMENDED_FIELDS = [
    "year",
    "mileage",
    "fuel",
    "transmission",
    "contact_number",
    "description",
    "images",
]


# ============================================================
# BASIC VALIDATION HELPERS
# ============================================================

def _is_valid_title(title: Any) -> bool:
    """Validate vehicle title."""

    if title is None:
        return False

    title = str(title).strip()

    return 3 <= len(title) <= 200


def _is_valid_price(price: Any) -> bool:
    """Validate that price is a positive number."""

    try:
        return float(price) > 0
    except (TypeError, ValueError):
        return False


def _is_valid_year(year: Any) -> bool:
    """Validate vehicle year."""

    try:
        year = int(year)
    except (TypeError, ValueError):
        return False

    return 1900 <= year <= 2050


def _is_valid_mileage(mileage: Any) -> bool:
    """Validate vehicle mileage."""

    try:
        mileage = int(mileage)
    except (TypeError, ValueError):
        return False

    return 0 <= mileage <= 10_000_000


def _is_valid_seats(seats: Any) -> bool:
    """Validate number of seats."""

    try:
        seats = int(seats)
    except (TypeError, ValueError):
        return False

    return 1 <= seats <= 12


def _is_valid_string(value: Any) -> bool:
    """Check whether a value is a non-empty string."""

    if value is None:
        return False

    return bool(str(value).strip())


def _is_valid_list(value: Any) -> bool:
    """Check whether a value is a non-empty list."""

    return isinstance(value, list) and len(value) > 0


# ============================================================
# QUALITY SCORE
# ============================================================

def _calculate_quality_score(vehicle: Vehicle) -> float:
    """
    Calculate a quality score for a vehicle.

    The score is based on the presence of useful vehicle
    information rather than only the required fields.

    Returns:
        Quality score from 0 to 100.
    """

    fields_to_evaluate = [
        bool(vehicle.title),
        _is_valid_price(vehicle.price),
        vehicle.year is not None,
        vehicle.mileage is not None,
        _is_valid_string(vehicle.fuel),
        _is_valid_string(vehicle.transmission),
        _is_valid_string(vehicle.colour),
        _is_valid_string(vehicle.description),
        _is_valid_list(vehicle.images),
        _is_valid_string(vehicle.contact_number),
        _is_valid_string(vehicle.dealer_name),
        _is_valid_string(vehicle.location),
    ]

    total_fields = len(fields_to_evaluate)

    if total_fields == 0:
        return 0.0

    filled_fields = sum(
        1 for field in fields_to_evaluate if field
    )

    score = (filled_fields / total_fields) * 100

    return round(score, 2)


# ============================================================
# VEHICLE VALIDATION
# ============================================================

def validate_vehicle(vehicle: Vehicle) -> ValidationResult:
    """
    Validate a normalized Vehicle record.

    Required fields:
        - title
        - price

    Recommended fields generate warnings when missing,
    but do not automatically make the record invalid.

    Args:
        vehicle:
            Normalized Vehicle object.

    Returns:
        ValidationResult containing:
        - valid
        - errors
        - warnings
        - quality_score
    """

    errors: list[str] = []
    warnings: list[str] = []

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if vehicle is None:
        return ValidationResult(
            id="unknown",
            valid=False,
            errors=["Vehicle record is missing"],
            warnings=[],
            quality_score=0.0,
        )

    # ========================================================
    # REQUIRED FIELD VALIDATION
    # ========================================================

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if not vehicle.title:
        errors.append(
            "Title is missing"
        )

    elif not _is_valid_title(vehicle.title):
        errors.append(
            "Title is invalid (must be between 3 and 200 characters)"
        )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    if vehicle.price is None:
        errors.append(
            "Price is missing"
        )

    elif not _is_valid_price(vehicle.price):
        errors.append(
            "Price must be greater than zero"
        )

    # ========================================================
    # OPTIONAL FIELD VALIDATION
    # ========================================================

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    if vehicle.year is not None:

        if not _is_valid_year(vehicle.year):

            warnings.append(
                f"Year {vehicle.year} is outside the normal range "
                f"(1900-2050)"
            )

    else:

        warnings.append(
            "Vehicle year is missing"
        )

    # --------------------------------------------------------
    # Mileage
    # --------------------------------------------------------

    if vehicle.mileage is not None:

        if not _is_valid_mileage(vehicle.mileage):

            warnings.append(
                f"Mileage {vehicle.mileage} seems unrealistic"
            )

    else:

        warnings.append(
            "Mileage is missing"
        )

    # --------------------------------------------------------
    # Seats
    # --------------------------------------------------------

    if vehicle.seats is not None:

        if not _is_valid_seats(vehicle.seats):

            warnings.append(
                f"Seat count {vehicle.seats} is invalid "
                f"(must be between 1 and 12)"
            )

    # --------------------------------------------------------
    # Fuel
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.fuel):

        warnings.append(
            "Fuel type is missing"
        )

    # --------------------------------------------------------
    # Transmission
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.transmission):

        warnings.append(
            "Transmission type is missing"
        )

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.description):

        warnings.append(
            "Description is missing"
        )

    else:

        description_length = len(
            str(vehicle.description).strip()
        )

        if description_length < 10:

            warnings.append(
                "Description is too short "
                "(recommended minimum: 10 characters)"
            )

        elif description_length > 5000:

            warnings.append(
                "Description is unusually long "
                "(over 5000 characters)"
            )

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    if not _is_valid_list(vehicle.images):

        warnings.append(
            "No images provided"
        )

    else:

        invalid_images = [
            image
            for image in vehicle.images
            if not isinstance(image, str)
            or not image.strip()
        ]

        if invalid_images:

            warnings.append(
                "One or more image paths/URLs are invalid"
            )

    # --------------------------------------------------------
    # Contact number
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.contact_number):

        warnings.append(
            "No contact number provided"
        )

    # --------------------------------------------------------
    # Dealer name
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.dealer_name):

        warnings.append(
            "Dealer/seller name is missing"
        )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    if not _is_valid_string(vehicle.location):

        warnings.append(
            "Vehicle location is missing"
        )

    # ========================================================
    # BASIC CONSISTENCY CHECKS
    # ========================================================

    # Year should not be in the future relative to the
    # configured upper validation limit.
    if vehicle.year is not None:

        if vehicle.year > 2050:

            warnings.append(
                f"Vehicle year {vehicle.year} is unusually high"
            )

    # Mileage should not be negative.
    if vehicle.mileage is not None:

        if vehicle.mileage < 0:

            warnings.append(
                "Mileage cannot be negative"
            )

    # Price should be positive.
    if vehicle.price is not None:

        try:

            if float(vehicle.price) <= 0:

                errors.append(
                    "Price must be greater than zero"
                )

        except (TypeError, ValueError):

            errors.append(
                "Price contains an invalid value"
            )

    # ========================================================
    # QUALITY SCORE
    # ========================================================

    quality_score = _calculate_quality_score(
        vehicle
    )

    # ========================================================
    # VALIDITY
    # ========================================================

    # Only errors make a vehicle invalid.
    #
    # Warnings are quality issues but should not prevent
    # processing unless the batch processor explicitly
    # chooses to enforce them.
    is_valid = len(errors) == 0

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return ValidationResult(
        id=vehicle.id,
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        quality_score=quality_score,
    )


# ============================================================
# MULTIPLE RECORD VALIDATION
# ============================================================

def validate_records(
    vehicles: list[Vehicle],
) -> tuple[list[Vehicle], list[ValidationResult]]:
    """
    Validate multiple vehicle records.

    Args:
        vehicles:
            List of normalized Vehicle objects.

    Returns:
        Tuple containing:

        valid_vehicles:
            Vehicles that passed validation.

        validation_results:
            ValidationResult for every vehicle.
    """

    valid_vehicles: list[Vehicle] = []
    validation_results: list[ValidationResult] = []

    for vehicle in vehicles:

        result = validate_vehicle(
            vehicle
        )

        validation_results.append(
            result
        )

        if result.valid:

            valid_vehicles.append(
                vehicle
            )

    return (
        valid_vehicles,
        validation_results,
    )


# ============================================================
# VALIDATION SUMMARY
# ============================================================

def get_validation_summary(
    results: list[ValidationResult],
) -> dict[str, Any]:
    """
    Generate a summary of validation results.

    Args:
        results:
            List of ValidationResult objects.

    Returns:
        Dictionary containing validation statistics.
    """

    total = len(results)

    valid = sum(
        1
        for result in results
        if result.valid
    )

    invalid = total - valid

    warning_count = sum(
        len(result.warnings)
        for result in results
    )

    error_count = sum(
        len(result.errors)
        for result in results
    )

    if total > 0:

        average_quality = round(
            sum(
                result.quality_score
                for result in results
            ) / total,
            2,
        )

    else:

        average_quality = 0.0

    return {
        "total_records": total,
        "valid_records": valid,
        "invalid_records": invalid,
        "error_count": error_count,
        "warning_count": warning_count,
        "average_quality_score": average_quality,
    }