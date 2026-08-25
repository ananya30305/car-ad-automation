from .models import CanonicalVehicle, ProcessingRecord, StageResult
from .normalizer import canonicalize_record

__all__ = [
    "CanonicalVehicle",
    "ProcessingRecord",
    "StageResult",
    "canonicalize_record",
]
