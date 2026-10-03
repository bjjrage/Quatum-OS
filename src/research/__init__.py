"""Research Infrastructure Package for Trading / Quant OS."""
from .pit_loader import PointInTimeDataLoader, SyntheticMarketGenerator
from .features import FeatureEngine, BarAggregator
from .events import EventDetector, PriceImpulseEvent
from .experiments import ExperimentRecord, ExperimentRegistry
from .parameters import (
    ResearchParameterSet,
    ParameterSetStatus,
    compute_parameter_fingerprint,
)
from .holdout import (
    SealedHoldoutManager,
    HoldoutAuditRecord,
    HoldoutViolationError,
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
    "ResearchParameterSet",
    "ParameterSetStatus",
    "compute_parameter_fingerprint",
    "SealedHoldoutManager",
    "HoldoutAuditRecord",
    "HoldoutViolationError",
]
