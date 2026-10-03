"""Strategy domain models, counterparty thesis, and lifecycle specifications for Trading / Quant OS.

Core Governance Rules:
1. NO STRATEGY IS PRIVILEGED BY ORIGIN.
2. THE OS DOES NOT SELECT THE BEST BACKTEST.
3. RESEARCH -> VALIDATION IS FORBIDDEN WITHOUT A COMPLETE COUNTERPARTY THESIS.
4. ALL MANUAL OR HEURISTIC RULES START AS INTUITION_UNVALIDATED.
5. ZERO LIVE CAPITAL INVARIANT ($0 LIVE RISK).
"""

from enum import Enum
import time
from typing import Dict, Any, List, Optional, Set, Union
from pydantic import BaseModel, Field, ConfigDict, computed_field, model_validator


class StrategyOrigin(str, Enum):
    """Origin of a strategy candidate. Metadata only - confers zero privilege."""
    HUMAN = "HUMAN"
    QUANT = "QUANT"
    STATISTICAL = "STATISTICAL"
    ML = "ML"
    AI_RESEARCH = "AI_RESEARCH"


class StrategyStage(str, Enum):
    """Lifecycle stages through evidence-gated promotion pipeline.
    Note: DISCOVERY is a Strategy Factory process, NOT a StrategyStage.
    The primary gate is RESEARCH -> VALIDATION.
    """
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"
    PAPER = "PAPER"
    SMALL_LIVE = "SMALL_LIVE"
    ACTIVE = "ACTIVE"
    REDUCED = "REDUCED"
    PAUSED = "PAUSED"
    KILLED = "KILLED"
    ARCHIVED = "ARCHIVED"


class StrategyFamily(str, Enum):
    """Core recognized strategy families. Arbitrary custom families are also supported."""
    RELATIVE_VALUE = "RELATIVE_VALUE"
    CROSS_MARKET = "CROSS_MARKET"
    FUNDING_BASIS = "FUNDING_BASIS"
    STATISTICAL_ARBITRAGE = "STATISTICAL_ARBITRAGE"
    CROSS_ASSET = "CROSS_ASSET"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BEHAVIORAL = "BEHAVIORAL"
    VOLATILITY = "VOLATILITY"
    OPTIONS = "OPTIONS"
    EVENT_NEWS = "EVENT_NEWS"
    LIQUIDITY_MICROSTRUCTURE = "LIQUIDITY_MICROSTRUCTURE"
    MARKET_MAKING = "MARKET_MAKING"
    ML_ALPHA = "ML_ALPHA"
    REGIME_SPECIFIC = "REGIME_SPECIFIC"
    PREDICTION_MARKETS = "PREDICTION_MARKETS"
    ON_CHAIN = "ON_CHAIN"
    CUSTOM = "CUSTOM"


class CounterpartyThesisStatus(str, Enum):
    UNVALIDATED = "UNVALIDATED"
    RESEARCH_HYPOTHESIS = "RESEARCH_HYPOTHESIS"
    SUPPORTED = "SUPPORTED"
    FALSIFIED = "FALSIFIED"


class CounterpartyThesis(BaseModel):
    """Structured economic thesis identifying who is paying the edge and why.
    
    Must answer:
    - WHO IS PAYING US?
    - WHY ARE THEY PAYING US?
    - WHY CAN'T OR WON'T THEY WAIT?
    - WHY SHOULD THE IMPACT BE TRANSIENT?
    - WHEN WOULD IT INSTEAD REPRESENT PERSISTENT INFORMATION?
    - WHAT WOULD FALSIFY THIS THESIS?
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    counterparty_type: str = Field(..., description="Who is paying us? (e.g. Urgent liquidity demander, hedger, segmented arbitrageur)")
    economic_mechanism: str = Field(..., description="Why are they paying us? (e.g. Inventory imbalance, forced liquidation, structural barrier)")
    why_trade_now: str = Field(..., description="Why can't or won't they wait? (e.g. Stop cascade, margin call, time constraint)")
    why_impact_may_be_transient: str = Field(..., description="Why should the price impact revert rather than persist?")
    why_it_may_be_information: str = Field(..., description="Under what conditions does this move represent persistent informational repricing?")
    observable_evidence: List[str] = Field(default_factory=list, description="Measurable market signals supporting this thesis")
    falsification_conditions: List[str] = Field(..., description="Explicit conditions that falsify and reject this thesis")
    evidence_status: CounterpartyThesisStatus = Field(default=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS)

    def is_complete_for_validation(self) -> bool:
        """RESEARCH -> VALIDATION is strictly FORBIDDEN without a complete counterparty thesis."""
        return (
            bool(self.counterparty_type.strip()) and
            bool(self.economic_mechanism.strip()) and
            bool(self.why_trade_now.strip()) and
            bool(self.why_impact_may_be_transient.strip()) and
            bool(self.why_it_may_be_information.strip()) and
            len(self.falsification_conditions) > 0 and
            all(bool(c.strip()) for c in self.falsification_conditions) and
            self.evidence_status != CounterpartyThesisStatus.FALSIFIED
        )


class StrategyRuleEvidenceStatus(str, Enum):
    """Evidence provenance hierarchy for strategy heuristics and rules."""
    INTUITION_UNVALIDATED = "INTUITION_UNVALIDATED"
    RESEARCH_SUPPORTED = "RESEARCH_SUPPORTED"
    BACKTEST_VALIDATED = "BACKTEST_VALIDATED"
    HOLDOUT_VALIDATED = "HOLDOUT_VALIDATED"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    LIVE_OBSERVED = "LIVE_OBSERVED"


class StrategyRuleEvidence(BaseModel):
    """Evidence provenance tracking for an individual heuristic or rule."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    strategy_id: str
    description: str
    status: StrategyRuleEvidenceStatus = StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED
    experiment_ids: List[str] = Field(default_factory=list)
    strategy_version: str = "1.0.0"
    first_proposed_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    last_validated_at: Optional[str] = None
    notes: str = ""


class StrategyParameterSet(BaseModel):
    """Typed parameter configuration container for strategy families."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    parameter_set_id: str = "DEFAULT"
    family: str = "CUSTOM"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"

    @model_validator(mode="before")
    @classmethod
    def _coerce_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            known = {"parameter_set_id", "family", "parameters", "version"}
            if not any(k in data for k in known):
                return {"parameters": data}
            elif "parameters" not in data:
                extra_params = {k: v for k, v in data.items() if k not in known}
                cleaned = {k: v for k, v in data.items() if k in known}
                cleaned["parameters"] = extra_params
                return cleaned
        return data

    def __getitem__(self, item: str) -> Any:
        return self.parameters[item]

    def get(self, item: str, default: Any = None) -> Any:
        return self.parameters.get(item, default)

    def __contains__(self, item: str) -> bool:
        return item in self.parameters


# Deterministic lifecycle stage transition graph
VALID_STAGE_TRANSITIONS: Dict[StrategyStage, Set[StrategyStage]] = {
    StrategyStage.IDEA: {
        StrategyStage.RESEARCH,
        StrategyStage.KILLED,
    },
    StrategyStage.RESEARCH: {
        StrategyStage.VALIDATION,
        StrategyStage.KILLED,
    },
    StrategyStage.VALIDATION: {
        StrategyStage.HOLDOUT,
        StrategyStage.KILLED,
    },
    StrategyStage.HOLDOUT: {
        StrategyStage.PAPER,
        StrategyStage.KILLED,
    },
    StrategyStage.PAPER: {
        StrategyStage.SMALL_LIVE,
        StrategyStage.KILLED,
    },
    StrategyStage.SMALL_LIVE: {
        StrategyStage.ACTIVE,
        StrategyStage.REDUCED,
        StrategyStage.PAUSED,
        StrategyStage.KILLED,
    },
    StrategyStage.ACTIVE: {
        StrategyStage.REDUCED,
        StrategyStage.PAUSED,
        StrategyStage.KILLED,
    },
    StrategyStage.REDUCED: {
        StrategyStage.ACTIVE,
        StrategyStage.PAUSED,
        StrategyStage.KILLED,
    },
    StrategyStage.PAUSED: {
        StrategyStage.ACTIVE,
        StrategyStage.REDUCED,
        StrategyStage.KILLED,
    },
    StrategyStage.KILLED: {
        StrategyStage.ARCHIVED,
    },
    StrategyStage.ARCHIVED: set(),  # Terminal state: no outbound transitions permitted
}


FORBIDDEN_PROVENANCE_PLACEHOLDERS: Set[str] = {
    "unknown",
    "unspecified",
    "provenance_missing",
    "ds_prov_unspecified",
    "cfg_prov_unspecified",
    "provenance_unspecified",
    "none",
    "null",
    "undefined",
}


class PromotionEvidenceBundle(BaseModel):
    """Immutable evidence bundle binding research artifacts, gate evaluations, and holdout records."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str
    strategy_version: str = "1.0.0"
    source_stage: StrategyStage
    target_stage: StrategyStage
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    git_sha: str
    gate_bundle_id: Optional[str] = None
    gate_bundle: Optional[Union[Dict[str, Any], List[Any]]] = None
    holdout_preregistration_id: Optional[str] = None
    holdout_access_id: Optional[str] = None
    holdout_result_id: Optional[str] = None
    created_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @model_validator(mode="before")
    @classmethod
    def _validate_bundle_provenance(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ("strategy_id", "strategy_version", "dataset_fingerprint", "config_fingerprint", "parameter_set_fingerprint", "git_sha"):
                v = data.get(field, "")
                if not str(v).strip():
                    raise ValueError(f"PromotionEvidenceBundle requires non-empty '{field}'.")
                if str(v).strip().lower() in FORBIDDEN_PROVENANCE_PLACEHOLDERS:
                    raise ValueError(f"PromotionEvidenceBundle field '{field}' contains prohibited placeholder '{v}'.")
        return data


class StrategySpec(BaseModel):
    """Specification and registration record of a strategy candidate.

    Contains metadata, origin, lifecycle stage, counterparty thesis, rule evidence,
    and empirical validation flags. No execution authority is granted by this specification.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str = Field(..., description="Unique strategy identifier (e.g. STR-001)")
    version: str = Field(default="1.0.0", description="Authoritative semantic version of the strategy specification")
    name: str = Field(..., description="Descriptive human-readable strategy name")
    family: str = Field(..., description="Strategy family classification")
    origin: StrategyOrigin = Field(..., description="Discovery source / origin (metadata only)")
    stage: StrategyStage = Field(default=StrategyStage.IDEA, description="Current lifecycle stage")
    description: str = Field(default="", description="Detailed thesis and hypothesis description")
    counterparty_thesis: Optional[CounterpartyThesis] = Field(
        default=None,
        description="Structured economic thesis. Mandatory before promotion to VALIDATION."
    )
    rules_evidence: List[StrategyRuleEvidence] = Field(
        default_factory=list,
        description="Evidence provenance for individual rules"
    )
    parameters: Optional[StrategyParameterSet] = Field(
        default=None,
        description="Typed parameter configuration container"
    )
    trial_count: int = Field(
        default=0,
        description="Number of empirical trials / parameter variants tested (selection bias tracking)"
    )
    math_foundation_validated: bool = Field(
        default=False,
        description="Whether mathematical foundations are validated"
    )
    economic_edge_validated: bool = Field(
        default=False,
        description="Whether out-of-sample economic edge is empirically validated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary strategy-specific metadata"
    )

    @computed_field
    @property
    def is_privileged(self) -> bool:
        """Core Governance Invariant: No strategy can technically be privileged. Always False."""
        return False

    @model_validator(mode="before")
    @classmethod
    def _reject_privileged_input(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("is_privileged"):
            raise ValueError("Core Governance Invariant Violated: No strategy may be marked privileged.")
        return data

    def model_copy(self, *, update: Optional[Dict[str, Any]] = None, deep: bool = False) -> "StrategySpec":
        """Harden model_copy against attempts to inject privilege via update dict."""
        if update:
            if update.get("is_privileged"):
                raise ValueError("Core Governance Invariant Violated: No strategy may be marked privileged via copy/update.")
            if "is_privileged" in update:
                update = {k: v for k, v in update.items() if k != "is_privileged"}
        return super().model_copy(update=update, deep=deep)
