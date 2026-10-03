"""Research Infrastructure Package for Trading / Quant OS."""
from .pit_loader import PointInTimeDataLoader, SyntheticMarketGenerator
from .features import FeatureEngine, BarAggregator
from .events import EventDetector, PriceImpulseEvent
from .experiments import (
    ExperimentRecord,
    ExperimentRegistry,
    RegistryIntegrityStatus,
    ExperimentRegistryIntegrityError,
)
from .parameters import (
    ResearchParameterSet,
    ParameterSetStatus,
    compute_parameter_fingerprint,
)
from .holdout import (
    SealedHoldoutManager,
    HoldoutAuditRecord,
    HoldoutViolationError,
    HoldoutAuditIntegrityError,
)

__all__ = [
    "PointInTimeDataLoader",
    "SyntheticMarketGenerator",
    "FeatureEngine",
    "BarAggregator",
    "EventDetector",
    "PriceImpulseEvent",
    "ExperimentRecord",
    "ExperimentRegistry",
    "RegistryIntegrityStatus",
    "ExperimentRegistryIntegrityError",
    "ResearchParameterSet",
    "ParameterSetStatus",
    "compute_parameter_fingerprint",
    "SealedHoldoutManager",
    "HoldoutAuditRecord",
    "HoldoutViolationError",
    "HoldoutAuditIntegrityError",
]
