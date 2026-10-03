"""Portfolio allocation package."""

from src.portfolio.allocator import (
    AllocationAction,
    AllocationBudget,
    PortfolioAllocator,
)
from src.portfolio.gates import (
    GateStatus,
    StrategyGateEvidenceSnapshot,
    StrategyGateResult,
    LatencySensitivityGate,
    TemporalStabilityGate,
    MultipleSelectionGate,
    CorrelationCapacityGate,
    all_gates_pass,
    validate_gate_bundle,
    benjamini_hochberg,
    expected_max_sharpe,
    deflated_sharpe_ratio,
)
from src.portfolio.regime import RegimeSnapshot

__all__ = [
    "AllocationAction",
    "AllocationBudget",
    "PortfolioAllocator",
    "GateStatus",
    "StrategyGateEvidenceSnapshot",
    "StrategyGateResult",
    "LatencySensitivityGate",
    "TemporalStabilityGate",
    "MultipleSelectionGate",
    "CorrelationCapacityGate",
    "all_gates_pass",
    "validate_gate_bundle",
    "benjamini_hochberg",
    "expected_max_sharpe",
    "deflated_sharpe_ratio",
    "RegimeSnapshot",
]
