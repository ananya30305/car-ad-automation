"""Canonical vehicle schema — boundary between extraction and posting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CanonicalVehicle:
    """Single normalized vehicle record used by every pipeline stage after ingest."""

    id: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None
    price: Optional[int] = None
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    fuel: Optional[str] = None
    drive_type: Optional[str] = None
    colour: Optional[str] = None
    condition: Optional[str] = None
    seats: Optional[int] = None
    features: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    description: Optional[str] = None
    contact_number: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    dealer_name: Optional[str] = None
    dealer_address: Optional[str] = None
    dealer_rating: Optional[str] = None
    title_description: Optional[str] = None
    pricing_summary: Optional[str] = None
    currency: str = "ZAR"
    category_path: list[str] = field(
        default_factory=lambda: [
            "Vehicles",
            "Cars - Parts",
            "Used cars in South Africa",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalVehicle":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = {k: v for k, v in data.items() if k in known}
        payload.setdefault("features", [])
        payload.setdefault("highlights", [])
        payload.setdefault("images", [])
        return cls(**payload)


@dataclass
class StageResult:
    id: str
    stage: str
    status: str  # ok | failed | rejected | skipped
    error: Optional[str] = None
    timestamp: str = field(default_factory=_utc_now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingRecord:
    id: str
    status: str
    stage: str
    error: Optional[str] = None
    timestamp: str = field(default_factory=_utc_now)
    history: list[StageResult] = field(default_factory=list)

    def add(self, result: StageResult) -> None:
        self.history.append(result)
        self.status = result.status
        self.stage = result.stage
        self.error = result.error
        self.timestamp = result.timestamp

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["history"] = [h.to_dict() for h in self.history]
        return data
