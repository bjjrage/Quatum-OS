"""
Research Parameter Set specification and fingerprinting.

Core Invariants:
1. Every strategy's parameter set must be explicitly represented as a versioned Pydantic model.
2. Changing any parameter changes the configuration fingerprint.
3. No parameter set with default values may be frozen as 'validated' policy.
4. Parameter set lifecycle tracks evidence progression: PROVISIONAL -> BACKTEST -> HOLDOUT -> PAPER.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ParameterSetStatus(str, Enum):
    """Evidence lifecycle status for research parameter sets."""
    PROVISIONAL = "PROVISIONAL"
    BACKTEST_SUPPORTED = "BACKTEST_SUPPORTED"
    HOLDOUT_SUPPORTED = "HOLDOUT_SUPPORTED"
    PAPER_SUPPORTED = "PAPER_SUPPORTED"


def compute_parameter_fingerprint(
    strategy_id: str,
    strategy_version: str,
    parameters: Dict[str, Any],
) -> str:
    """Compute deterministic SHA-256 fingerprint for a parameter configuration."""
    canonical_repr = {
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "parameters": parameters,
    }
    payload = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ResearchParameterSet(BaseModel):
    """
    Versioned, immutable parameter set governing an empirical strategy variant.
    """
    model_config = ConfigDict(extra="forbid")

    parameter_set_id: str = Field(..., description="Unique parameter set identifier")
    strategy_id: str = Field(..., description="Target strategy identifier (e.g. STR-001, STR-002)")
    strategy_version: str = Field(default="1.0.0", description="Semantic strategy version")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Concrete hyperparameter dictionary")
    status: ParameterSetStatus = Field(
        default=ParameterSetStatus.PROVISIONAL,
        description="Current evidence status. Defaults to PROVISIONAL research prior."
    )
    config_fingerprint: str = Field(
        default="",
        description="Deterministic hash of the strategy parameters"
    )

    def model_post_init(self, __context: Any) -> None:
        """Automatically ensure config_fingerprint is set from parameters."""
        expected_fp = compute_parameter_fingerprint(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            parameters=self.parameters,
        )
        if not self.config_fingerprint:
            object.__setattr__(self, "config_fingerprint", expected_fp)
        elif self.config_fingerprint != expected_fp:
            raise ValueError(
                f"Config fingerprint mismatch: expected {expected_fp[:12]} but got {self.config_fingerprint[:12]}. "
                "Changing any parameter must update the fingerprint."
            )

    @property
    def fingerprint(self) -> str:
        """Alias for config_fingerprint."""
        return self.config_fingerprint
