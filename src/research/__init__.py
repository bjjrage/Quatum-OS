"""Research Infrastructure Package for Trading / Quant OS."""
from .pit_loader import PointInTimeDataLoader, SyntheticMarketGenerator
from .features import FeatureEngine, BarAggregator
from .events import EventDetector, PriceImpulseEvent

__all__ = [
    "PointInTimeDataLoader",
    "SyntheticMarketGenerator",
    "FeatureEngine",
    "BarAggregator",
    "EventDetector",
    "PriceImpulseEvent",
]
