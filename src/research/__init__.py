"""Research Infrastructure Package for Trading / Quant OS."""
from .pit_loader import PointInTimeDataLoader, SyntheticMarketGenerator
from .features import FeatureEngine, BarAggregator
from .events import EventDetector, PriceImpulseEvent
from .experiments import (
    ExperimentRecord,
    ExperimentRegistry,
    RegistryIntegrityStatus,
    ExperimentRegistryIntegrityError,
    MultipleTestingContext,
)
from .parameters import (
    ResearchParameterSet,
    ParameterSetStatus,
    compute_parameter_fingerprint,
)
from .holdout import (
    SealedHoldoutManager,
    HoldoutStatus,
    HoldoutPreRegistration,
    HoldoutAccessRecord,
    HoldoutEvaluationResult,
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
    "MultipleTestingContext",
    "ResearchParameterSet",
    "ParameterSetStatus",
    "compute_parameter_fingerprint",
    "SealedHoldoutManager",
    "HoldoutStatus",
    "HoldoutPreRegistration",
    "HoldoutAccessRecord",
    "HoldoutEvaluationResult",
    "HoldoutAuditRecord",
    "HoldoutViolationError",
    "HoldoutAuditIntegrityError",
]
