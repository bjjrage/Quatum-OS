"""Strategy Registry: central inventory and lifecycle state tracker for candidate strategies.

Core Governance Rules:
1. NO STRATEGY IS PRIVILEGED BY ORIGIN.
2. The Strategy Registry is purely declarative: it has ZERO execution authority.
3. Duplicate strategy IDs are strictly rejected.
4. Stage transitions are strictly evidence-gated: arbitrary promotion skipping is rejected.
5. RESEARCH -> VALIDATION requires a complete, validated CounterpartyThesis.
"""

from typing import Dict, List, Optional
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
    CounterpartyThesis,
    CounterpartyThesisStatus,
    StrategyRuleEvidence,
    StrategyRuleEvidenceStatus,
    VALID_STAGE_TRANSITIONS,
)


class DuplicateStrategyError(Exception):
    """Raised when registering a strategy ID that already exists."""
    pass


class StrategyNotFoundError(Exception):
    """Raised when querying a strategy ID that does not exist."""
    pass


class InvalidStageTransitionError(Exception):
    """Raised when an illegal or gate-bypassing lifecycle stage transition is attempted."""
    pass


class StrategyRegistry:
    """In-memory declarative registry of all strategy candidates across lifecycle stages."""

    def __init__(self) -> None:
        self._strategies: Dict[str, StrategySpec] = {}

    def register(self, spec: StrategySpec) -> None:
        """Register a new strategy specification.

        Args:
            spec: Validated StrategySpec

        Raises:
            DuplicateStrategyError: If a strategy with the same ID already exists.
            ValueError: If spec violates lifecycle governance or registration invariants.
        """
        if not isinstance(spec, StrategySpec):
            raise TypeError(f"Expected StrategySpec instance, got {type(spec).__name__}")

        if spec.strategy_id in self._strategies:
            raise DuplicateStrategyError(
                f"Strategy with ID '{spec.strategy_id}' is already registered."
            )

        # Invariant: registering directly as ACTIVE or SMALL_LIVE without validated economic edge is rejected
        if spec.stage in (StrategyStage.ACTIVE, StrategyStage.SMALL_LIVE):
            if not spec.economic_edge_validated:
                raise ValueError(
                    f"Cannot register strategy '{spec.strategy_id}' as {spec.stage.value}: "
                    "economic_edge_validated is False. Promotion requires passing portfolio evidence gates."
                )
            else:
                raise ValueError(
                    f"Cannot register strategy '{spec.strategy_id}' directly as {spec.stage.value}. "
                    "All candidates must enter at IDEA or RESEARCH and progress through evidence gates."
                )


        # Invariant: registering past RESEARCH stage requires complete CounterpartyThesis
        if spec.stage not in (StrategyStage.IDEA, StrategyStage.RESEARCH):
            if spec.counterparty_thesis is None or not spec.counterparty_thesis.is_complete_for_validation():
                raise ValueError(
                    f"Cannot register strategy '{spec.strategy_id}' in stage {spec.stage.value} "
                    "without a complete CounterpartyThesis including falsification conditions."
                )

        self._strategies[spec.strategy_id] = spec

    def get(self, strategy_id: str) -> StrategySpec:
        """Retrieve a strategy specification by ID."""
        if strategy_id not in self._strategies:
            raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found in registry.")
        return self._strategies[strategy_id]

    def list_all(self) -> List[StrategySpec]:
        """Return all registered strategy specifications in registration order."""
        return list(self._strategies.values())

    def list_by_stage(self, stage: StrategyStage) -> List[StrategySpec]:
        """Filter strategies by lifecycle stage."""
        return [s for s in self._strategies.values() if s.stage == stage]

    def list_by_family(self, family: str) -> List[StrategySpec]:
        """Filter strategies by family name."""
        return [s for s in self._strategies.values() if s.family == family]

    def list_by_origin(self, origin: StrategyOrigin) -> List[StrategySpec]:
        """Filter strategies by origin."""
        return [s for s in self._strategies.values() if s.origin == origin]

    def update_stage(self, strategy_id: str, new_stage: StrategyStage) -> None:
        """Update the lifecycle stage of a registered strategy, enforcing evidence-gated transitions.

        Raises:
            StrategyNotFoundError: If strategy_id is not registered.
            InvalidStageTransitionError: If the requested transition bypasses gates or violates the lifecycle graph.
        """
        spec = self.get(strategy_id)
        current_stage = spec.stage

        if current_stage == new_stage:
            return

        allowed = VALID_STAGE_TRANSITIONS.get(current_stage, set())
        if new_stage not in allowed:
            raise InvalidStageTransitionError(
                f"Invalid stage transition for strategy '{strategy_id}': "
                f"cannot transition from {current_stage.value} to {new_stage.value}."
            )

        # Governance Gate: RESEARCH -> VALIDATION requires complete CounterpartyThesis
        if current_stage == StrategyStage.RESEARCH and new_stage == StrategyStage.VALIDATION:
            if spec.counterparty_thesis is None or not spec.counterparty_thesis.is_complete_for_validation():
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition from RESEARCH to VALIDATION: "
                    "Counterparty thesis is missing, incomplete, or lacks falsification conditions."
                )

        updated = spec.model_copy(update={"stage": new_stage})
        self._strategies[strategy_id] = updated

    @staticmethod
    def has_execution_authority() -> bool:
        """Non-negotiable architectural invariant:
        The Strategy Registry is purely metadata and inventory.
        It has ZERO execution authority, cannot place orders, and cannot touch capital.
        """
        return False


def get_seed_str_001() -> StrategySpec:
    """Return standard specification for Seed Research Program STR-001."""
    thesis = CounterpartyThesis(
        counterparty_type="Segmented prediction market participants vs institutional derivatives market makers",
        economic_mechanism="Cross-market friction, capital constraints, different pricing models, and directional urgency",
        why_trade_now="Prediction market participants demand immediate execution for binary event hedges",
        why_impact_may_be_transient="Divergences between option-implied probability surfaces and binary outcome prices contract as arbitrage capital operates",
        why_it_may_be_information="Prediction markets may incorporate non-price regulatory or political information before options markets adjust",
        observable_evidence=[
            "Polymarket-Deribit probability spread exceeds total round-trip hurdle",
            "Deribit smile arbitrage absence confirmed",
        ],
        falsification_conditions=[
            "Net expectancy fails to exceed taker fees and execution slippage",
            "Divergence fails to mean-revert or resolve prior to contract expiry",
        ],
        evidence_status=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS,
    )

    return StrategySpec(
        strategy_id="STR-001",
        name="Polymarket x Deribit Relative Value",
        family=StrategyFamily.RELATIVE_VALUE.value,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        description="Cross-market relative value between Polymarket binary contracts and Deribit options.",
        counterparty_thesis=thesis,
        math_foundation_validated=True,
        economic_edge_validated=False,
        metadata={"seed_program": "Line A", "reference_market": "BTC/ETH"},
    )


def get_seed_str_002() -> StrategySpec:
    """Return standard specification for Seed Research Program STR-002 v2.

    Preserves original hypothesis:
    Extreme short-horizon price impulses, normalized by prior volatility,
    may exhibit an exploitable overshoot followed by retracement.
    Execution is strictly LONG-ONLY; short-side observations are research only.
    """
    thesis = CounterpartyThesis(
        counterparty_type="Forced sellers, cascading liquidation algorithms, and distressed de-risking participants",
        economic_mechanism="Microstructure liquidity depletion and order book sweeping produce transient overshoot beyond fundamental value",
        why_trade_now="Automated margin liquidation protocols or stop cascades execute via market orders without price discretion",
        why_impact_may_be_transient="Once forced aggressive selling exhausts and book replenishes, prices retrace toward pre-shock reference levels",
        why_it_may_be_information="Hacks, delistings, smart-contract exploits, or fundamental project impairments represent permanent repricing",
        observable_evidence=[
            "Negative altcoin impulse residual after controlling for BTC and ETH movements",
            "First reversal confirmation on 1-second bar structure or book replenishment",
            "Presence of forced liquidation flags (!forceOrder@arr)",
        ],
        falsification_conditions=[
            "Post-impulse residual continues downward drift without statistical retracement",
            "Expected rebound is smaller than round-trip taker fees and execution slippage",
            "Strategy failure rate in high-volatility regimes exceeds risk bounds",
        ],
        evidence_status=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS,
    )

    rules = [
        StrategyRuleEvidence(
            rule_id="RULE-STR002-001",
            strategy_id="STR-002",
            description="BTC state down / running hard -> block entry or exit early",
            status=StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED,
            notes="Owner manual intuition: avoid catching falling knives when systemic market is falling.",
        ),
        StrategyRuleEvidence(
            rule_id="RULE-STR002-002",
            strategy_id="STR-002",
            description="First reversal entry confirmation (no immediate knife catch)",
            status=StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED,
            notes="Require higher-low on 1s bars or book replenishment before trigger.",
        ),
        StrategyRuleEvidence(
            rule_id="RULE-STR002-003",
            strategy_id="STR-002",
            description="Strictly long-only execution (short side research only)",
            status=StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED,
            notes="Asymmetry in liquidation mechanics: long squeeze mechanics differ from short cascades.",
        ),
        StrategyRuleEvidence(
            rule_id="RULE-STR002-004",
            strategy_id="STR-002",
            description="Reference price exit target (pre-shock VWAP / origin price)",
            status=StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED,
            notes="Target pre-shock equilibrium rather than arbitrary fixed percentages.",
        ),
        StrategyRuleEvidence(
            rule_id="RULE-STR002-005",
            strategy_id="STR-002",
            description="BTC supportive / flat -> allow runner / extended hold",
            status=StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED,
            notes="Trail stops when systematic market supports the asset recovery.",
        ),
    ]

    return StrategySpec(
        strategy_id="STR-002",
        name="Impulse / Overshoot / Short-Horizon Retracement",
        family=StrategyFamily.BEHAVIORAL.value,
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.RESEARCH,
        description=(
            "Extreme short-horizon price impulses, normalized by prior volatility, "
            "may exhibit an exploitable overshoot followed by retracement. "
            "Execution is strictly LONG-ONLY; short side is research only."
        ),
        counterparty_thesis=thesis,
        rules_evidence=rules,
        math_foundation_validated=False,
        economic_edge_validated=False,
        metadata={
            "seed_program": "Line B",
            "reference_market": "Binance USD(S)-M",
            "thesis": (
                "Extreme short-horizon price impulses, normalized by prior volatility, "
                "may exhibit an exploitable overshoot followed by retracement."
            ),
            "move_types": {
                "informative_move": "Hack / delisting / fundamental news / regulatory event -> may rationally NOT revert",
                "forced_liquidity_move": "Liquidations / stops / deleveraging / panic / liquidity withdrawal -> may overshoot and retrace",
            },
            "version": "2.0.0",
            "display_name": "STR-002 v2 — Liquidity Shock Reversal",
            "execution_mode": "LONG_ONLY",
            "short_side": "RESEARCH_ONLY",
            "research_dimensions": [
                "impulse_magnitude",
                "prior_realized_volatility",
                "forward_return",
                "retracement_ratio",
                "mfe",
                "mae",
                "time_to_retracement",
                "liquidity",
                "spread",
                "depth",
                "funding",
                "open_interest",
                "forced_liquidations",
                "market_regime",
            ],
            "feature_notes": "Orderbook information is an evaluation feature, not the definition of the strategy.",
        },
    )


def get_seed_str_003() -> StrategySpec:
    """Return standard specification for STR-003: Scheduled Supply Events / Unlock Overshoot."""
    thesis = CounterpartyThesis(
        counterparty_type="Token unlock recipients, early venture investors, and treasury liquidators",
        economic_mechanism="Structural supply expansion creates temporary orderbook overhang exceeding short-term market absorption",
        why_trade_now="Contractual vestings release tokens at deterministic block/calendar times",
        why_impact_may_be_transient="Market over-discounts the unlock event prior to execution; post-unlock volume stabilizes",
        why_it_may_be_information="Major venture unlocks leading to sustained treasury exit represent fundamental dilutive repricing",
        observable_evidence=[
            "On-chain transfer volume from vesting contracts to exchange deposit addresses",
            "Derivatives basis discount expansion prior to unlock event",
        ],
        falsification_conditions=[
            "Unlock supply is absorbed with zero volatility discount",
            "Post-unlock price continues downward trend for >30 days without mean reversion",
        ],
        evidence_status=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS,
    )

    return StrategySpec(
        strategy_id="STR-003",
        name="Scheduled Supply Events / Unlock Overshoot",
        family=StrategyFamily.EVENT_NEWS.value,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        description="Exploiting microstructure and basis dislocations around scheduled token unlock events.",
        counterparty_thesis=thesis,
        math_foundation_validated=False,
        economic_edge_validated=False,
        metadata={"seed_program": "Supply Dynamics", "target_universe": "Tier 2-4 Vesting Tokens"},
    )


def get_seed_pump_fun_copy() -> StrategySpec:
    """Return specification for Pump.fun Copytrading research candidate.
    
    Strict Invariant: RESEARCH stage only, strictly $0 capital, strictly on-chain if ever validated.
    """
    thesis = CounterpartyThesis(
        counterparty_type="Retail liquidity participants in micro-cap bonding curves",
        economic_mechanism="Information asymmetry and execution speed advantages on newly deployed token curves",
        why_trade_now="Rapid bonding curve progression creates intense FOMO and immediate retail taker volume",
        why_impact_may_be_transient="Micro-cap memecoins rapidly collapse after bonding curve migration or developer exit",
        why_it_may_be_information="Developer wallet activity and liquidity extraction represent permanent rug/loss",
        observable_evidence=[
            "Cluster wallet transaction graph analysis",
            "Mempool transaction timing metrics",
        ],
        falsification_conditions=[
            "On-chain gas, priority fees, and sandwich attack slippage exceed gross trading PnL",
            "Copy-target wallet alpha decays to zero out-of-sample",
        ],
        evidence_status=CounterpartyThesisStatus.UNVALIDATED,
    )

    return StrategySpec(
        strategy_id="STR-PUMP-COPY",
        name="Pump.fun Copytrading Research",
        family=StrategyFamily.ON_CHAIN.value,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.RESEARCH,
        description="On-chain wallet tracking and token deployment copytrading research. Strictly $0 capital.",
        counterparty_thesis=thesis,
        math_foundation_validated=False,
        economic_edge_validated=False,
        metadata={"on_chain_only": True, "prop_eligible": False, "capital_pocket_allowed": "OWN_ONLY"},
    )


def create_default_registry() -> StrategyRegistry:
    """Factory creating a StrategyRegistry populated with baseline seed research programs."""
    registry = StrategyRegistry()
    registry.register(get_seed_str_001())
    registry.register(get_seed_str_002())
    return registry


def create_extended_registry() -> StrategyRegistry:
    """Factory creating a StrategyRegistry populated with all standard seed research programs including v1.4 additions."""
    registry = create_default_registry()
    registry.register(get_seed_str_003())
    registry.register(get_seed_pump_fun_copy())
    return registry
