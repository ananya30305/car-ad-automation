"""Typed data models for vehicle advertisements."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class VehicleCondition(Enum):
    """Vehicle condition state."""
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"


class TransmissionType(Enum):
    """Transmission types."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CVT = "cvt"


class FuelType(Enum):
    """Fuel types."""
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"
    LPG = "lpg"
    CNG = "cng"


class DriveType(Enum):
    """Drive types."""
    FWD = "fwd"
    RWD = "rwd"
    AWD = "awd"
    FOUR_WD = "4wd"


@dataclass
class Vehicle:
    """Normalized vehicle record."""
    
    id: str  # stock_id or unique identifier
    title: str
    price: int
    condition: str = "used"
    year: Optional[int] = None
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    fuel: Optional[str] = None
    drive_type: Optional[str] = None
    colour: Optional[str] = None
    seats: Optional[int] = None
    description: Optional[str] = None
    
    # Contact/Location
    dealer_name: Optional[str] = None
    dealer_address: Optional[str] = None
    contact_number: Optional[str] = None
    location: Optional[str] = None
    
    # Features and highlights
    features: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    
    # Images
    images: list[str] = field(default_factory=list)
    
    # Currency
    currency: str = "ZAR"
    
    # Metadata
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def has_required_fields(self) -> bool:
        """Check if record has all required fields."""
        return bool(self.title and self.price)


@dataclass
class ValidationResult:
    """Validation result for a record."""
    
    id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DuplicateCheckResult:
    """Result of duplicate checking."""
    
    id: str
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    fingerprint: Optional[str] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ProcessingStep:
    """A single processing step."""
    
    name: str
    status: str  # "pending", "in_progress", "completed", "failed"
    error: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Advertisement:
    """Complete advertisement ready for posting."""
    
    id: str
    vehicle: Vehicle
    validation: ValidationResult
    description_generated: bool = False
    images_validated: bool = False
    ready_to_post: bool = False
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, including nested objects."""
        data = asdict(self)
        data['vehicle'] = self.vehicle.to_dict()
        data['validation'] = self.validation.to_dict()
        return data


@dataclass
class SubmissionResult:
    """Result of posting an advertisement."""
    
    id: str
    submitted: bool
    status: str  # "submitted", "failed", "skipped"
    url: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BatchProcessingReport:
    """Final report for batch processing."""
    
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicates: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    missing_images: int = 0
    verification_failures: int = 0
    submission_failures: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    runtime_seconds: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
