"""Typed data models for vehicle advertisement automation."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS
# ============================================================

class VehicleCondition(Enum):
    """Vehicle condition state."""

    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"


class TransmissionType(Enum):
    """Vehicle transmission types."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CVT = "cvt"


class FuelType(Enum):
    """Vehicle fuel types."""

    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"
    LPG = "lpg"
    CNG = "cng"


class DriveType(Enum):
    """Vehicle drivetrain types."""

    FWD = "fwd"
    RWD = "rwd"
    AWD = "awd"
    FOUR_WD = "4wd"


# ============================================================
# VEHICLE
# ============================================================

@dataclass
class Vehicle:
    """
    Normalized vehicle record.

    This is the main data object passed through the automation
    pipeline.
    """

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    id: str
    title: str
    price: int

    # --------------------------------------------------------
    # Vehicle information
    # --------------------------------------------------------

    condition: str = "used"
    year: Optional[int] = None
    mileage: Optional[int] = None

    transmission: Optional[str] = None
    fuel: Optional[str] = None
    drive_type: Optional[str] = None

    colour: Optional[str] = None
    seats: Optional[int] = None

    # --------------------------------------------------------
    # Advertisement content
    # --------------------------------------------------------

    description: Optional[str] = None

    # --------------------------------------------------------
    # Dealer / seller information
    # --------------------------------------------------------

    dealer_name: Optional[str] = None
    dealer_address: Optional[str] = None
    contact_number: Optional[str] = None
    location: Optional[str] = None

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    features: list[str] = field(
        default_factory=list
    )

    highlights: list[str] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    images: list[str] = field(
        default_factory=list
    )

    downloaded_image_count: int = field(
        default=0,
        init=False
    )

    # --------------------------------------------------------
    # Currency
    # --------------------------------------------------------

    currency: str = "ZAR"

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    source_id: Optional[str] = None
    created_at: Optional[str] = None

    # ========================================================
    # METHODS
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert vehicle to a normal dictionary.

        Returns:
            Dictionary representation of the vehicle.
        """

        return asdict(self)

    def has_required_fields(self) -> bool:
        """
        Check whether the vehicle contains required fields.

        Returns:
            True when title and price are available.
        """

        return bool(
            self.title
            and str(self.title).strip()
            and self.price is not None
        )

    def get_description(self) -> str:
        """
        Return a safe description string.

        Returns:
            Vehicle description or empty string.
        """

        return str(
            self.description or ""
        ).strip()

    def get_images(self) -> list[str]:
        """
        Return a copy of the vehicle image list.

        Returns:
            List of image paths.
        """

        return list(
            self.images or []
        )


# ============================================================
# VALIDATION RESULT
# ============================================================

@dataclass
class ValidationResult:
    """Result of vehicle validation."""

    id: str

    valid: bool

    errors: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    quality_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert validation result to dictionary.
        """

        return asdict(self)


# ============================================================
# DUPLICATE CHECK RESULT
# ============================================================

@dataclass
class DuplicateCheckResult:
    """Result of duplicate detection."""

    id: str

    is_duplicate: bool

    duplicate_of: Optional[str] = None

    fingerprint: Optional[str] = None

    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert duplicate result to dictionary.
        """

        return asdict(self)


# ============================================================
# PROCESSING STEP
# ============================================================

@dataclass
class ProcessingStep:
    """
    Represents one processing step in the automation pipeline.
    """

    name: str

    status: str
    # Expected values:
    # pending
    # in_progress
    # completed
    # failed
    # skipped

    error: Optional[str] = None

    timestamp: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert processing step to dictionary.
        """

        return asdict(self)


# ============================================================
# ADVERTISEMENT
# ============================================================

@dataclass
class Advertisement:
    """
    Complete advertisement prepared for posting.
    """

    id: str

    vehicle: Vehicle

    validation: ValidationResult

    description_generated: bool = False

    images_validated: bool = False

    ready_to_post: bool = False

    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Automatically set creation timestamp when needed.
        """

        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert advertisement to dictionary.

        Nested Vehicle and ValidationResult objects are also
        converted into dictionaries.
        """

        return {
            "id": self.id,
            "vehicle": self.vehicle.to_dict(),
            "validation": self.validation.to_dict(),
            "description_generated": self.description_generated,
            "images_validated": self.images_validated,
            "ready_to_post": self.ready_to_post,
            "created_at": self.created_at,
        }


# ============================================================
# SUBMISSION RESULT
# ============================================================

@dataclass
class SubmissionResult:
    """
    Result of processing/submitting one advertisement.
    """

    id: str

    submitted: bool

    status: str
    # Examples:
    # VALIDATED
    # PREPARED
    # VERIFIED
    # FORM_FILLED
    # SUBMITTED
    # BLOCKED
    # FAILED
    # SKIPPED

    url: Optional[str] = None

    error: Optional[str] = None

    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Automatically add timestamp when one is not supplied.
        """

        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert submission result to dictionary.
        """

        return asdict(self)


# ============================================================
# BATCH PROCESSING REPORT
# ============================================================

@dataclass
class BatchProcessingReport:
    """
    Final report generated after processing a batch.
    """

    # --------------------------------------------------------
    # Record counts
    # --------------------------------------------------------

    total_records: int = 0

    valid_records: int = 0

    invalid_records: int = 0

    duplicates: int = 0

    # --------------------------------------------------------
    # Processing counts
    # --------------------------------------------------------

    processed: int = 0

    successful: int = 0

    failed: int = 0

    skipped: int = 0

    # --------------------------------------------------------
    # Image / verification / submission statistics
    # --------------------------------------------------------

    missing_images: int = 0

    downloaded_images_total: int = 0

    images_download_failed: int = 0

    verification_failures: int = 0

    submission_failures: int = 0

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    started_at: Optional[str] = None

    finished_at: Optional[str] = None

    runtime_seconds: float = 0.0

    # ========================================================
    # METHODS
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert report to dictionary.
        """

        return asdict(self)

    def mark_started(self) -> None:
        """Record batch start time."""

        self.started_at = datetime.now().isoformat()

    def mark_finished(self) -> None:
        """Record batch finish time and runtime."""

        self.finished_at = datetime.now().isoformat()

        if self.started_at:
            try:
                start = datetime.fromisoformat(
                    self.started_at
                )

                end = datetime.fromisoformat(
                    self.finished_at
                )

                self.runtime_seconds = (
                    end - start
                ).total_seconds()

            except Exception:
                pass

    def increment_success(self) -> None:
        """Record one successful processed advertisement."""

        self.processed += 1
        self.successful += 1

    def increment_failure(self) -> None:
        """Record one failed advertisement."""

        self.processed += 1
        self.failed += 1

    def increment_skipped(self) -> None:
        """Record one skipped advertisement."""

        self.skipped += 1

    def increment_verification_failure(self) -> None:
        """Record a form verification failure."""

        self.verification_failures += 1
        self.failed += 1

    def increment_submission_failure(self) -> None:
        """Record a submission failure."""

        self.submission_failures += 1
        self.failed += 1


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def enum_to_value(value: Any) -> Any:
    """
    Convert an Enum to its underlying value.

    Useful when serializing data.

    Args:
        value:
            Any Python value.

    Returns:
        Enum value or original value.
    """

    if isinstance(value, Enum):
        return value.value

    return value


def vehicle_to_dict(vehicle: Vehicle) -> dict[str, Any]:
    """
    Convenience function for converting a Vehicle to a dictionary.

    Args:
        vehicle:
            Vehicle object.

    Returns:
        Dictionary representation.
    """

    return vehicle.to_dict()