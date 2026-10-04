"""Strategy Registry: central inventory and lifecycle state tracker for candidate strategies.

Core Governance Rules:
1. NO STRATEGY IS PRIVILEGED BY ORIGIN.
2. The Strategy Registry is purely declarative: it has ZERO execution authority.
3. Duplicate strategy IDs are strictly rejected.
4. Stage transitions are strictly evidence-gated: arbitrary promotion skipping is rejected.
5. RESEARCH -> VALIDATION requires a complete, validated CounterpartyThesis.
"""

from typing import Dict, List, Optional, Any
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
    CounterpartyThesis,
    CounterpartyThesisStatus,
    StrategyRuleEvidence,
    StrategyRuleEvidenceStatus,
    PromotionEvidenceBundle,
    VALID_STAGE_TRANSITIONS,
)
from src.portfolio.gates import validate_gate_bundle, GateStatus
from src.research.holdout import HoldoutStatus


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

    def __init__(
        self,
        holdout_manager: Optional[Any] = None,
        gate_store: Optional[Any] = None,
    ) -> None:
        self._strategies: Dict[str, StrategySpec] = {}
        self._holdout_manager = holdout_manager
        self._gate_store = gate_store

    def register(self, spec: StrategySpec, *, trusted_seed: bool = False) -> None:
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

        # Invariant: registering directly as ACTIVE or SMALL_LIVE is forbidden under USD 0 live capital
        if spec.stage in (StrategyStage.ACTIVE, StrategyStage.SMALL_LIVE):
            raise ValueError(
                f"Cannot register strategy '{spec.strategy_id}' directly as {spec.stage.value}. "
                "Authorized live capital is USD 0. Real capital allocation is permanently disabled."
            )

        # Invariant: a strategy cannot be registered past RESEARCH from outside the audited seed loader;
        # advancing requires update_stage() with an evidence bundle.
        if spec.stage not in (StrategyStage.IDEA, StrategyStage.RESEARCH) and not trusted_seed:
            raise ValueError(
                f"Cannot register strategy '{spec.strategy_id}' directly in stage {spec.stage.value}. "
                "Register in IDEA/RESEARCH and promote through update_stage() with an evidence bundle."
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

    def update_stage(
        self,
        strategy_id: str,
        new_stage: StrategyStage,
        evidence_bundle: Optional[PromotionEvidenceBundle] = None,
        holdout_manager: Optional[Any] = None,
        gate_store: Optional[Any] = None,
    ) -> None:
        """Update the lifecycle stage of a registered strategy, enforcing evidence-gated transitions.

        Raises:
            StrategyNotFoundError: If strategy_id is not registered.
            InvalidStageTransitionError: If the requested transition bypasses gates or violates the lifecycle graph.
        """
        mgr = holdout_manager if holdout_manager is not None else self._holdout_manager
        store = gate_store if gate_store is not None else self._gate_store

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

        # General EvidenceBundle validation if provided
        if evidence_bundle is not None:
            if evidence_bundle.strategy_id != strategy_id:
                raise InvalidStageTransitionError(
                    f"Strategy ID mismatch in evidence bundle: '{evidence_bundle.strategy_id}' != '{strategy_id}'."
                )
            if evidence_bundle.source_stage != current_stage:
                raise InvalidStageTransitionError(
                    f"Promotion evidence bundle source stage '{evidence_bundle.source_stage.value}' "
                    f"does not match current strategy stage '{current_stage.value}'."
                )
            if evidence_bundle.target_stage != new_stage:
                raise InvalidStageTransitionError(
                    f"Promotion evidence bundle target stage '{evidence_bundle.target_stage.value}' "
                    f"does not match requested new stage '{new_stage.value}'."
                )
            spec_version = getattr(spec, "version", None) or (spec.parameters.version if spec.parameters else None)
            if not spec_version:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' lacks authoritative version specification."
                )
            if evidence_bundle.strategy_version != spec_version:
                raise InvalidStageTransitionError(
                    f"Strategy version mismatch: bundle '{evidence_bundle.strategy_version}' != spec '{spec_version}'."
                )

        # 1. RESEARCH -> VALIDATION requires complete CounterpartyThesis
        if current_stage == StrategyStage.RESEARCH and new_stage == StrategyStage.VALIDATION:
            if spec.counterparty_thesis is None or not spec.counterparty_thesis.is_complete_for_validation():
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition from RESEARCH to VALIDATION: "
                    "Counterparty thesis is missing, incomplete, or lacks falsification conditions."
                )

        # 2. VALIDATION -> HOLDOUT requires PromotionEvidenceBundle with valid preregistration AND holdout_manager
        elif current_stage == StrategyStage.VALIDATION and new_stage == StrategyStage.HOLDOUT:
            if evidence_bundle is None:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition from VALIDATION to HOLDOUT: "
                    "PromotionEvidenceBundle is required."
                )
            if not evidence_bundle.holdout_preregistration_id:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition to HOLDOUT: "
                    "Evidence bundle lacks holdout_preregistration_id. Preregistration must exist before promotion."
                )
            if mgr is None:
                raise InvalidStageTransitionError(
                    "HOLDOUT_GOVERNANCE_STORE_REQUIRED: Strategy cannot transition from VALIDATION to HOLDOUT without authoritative holdout_manager."
                )
            if mgr.is_corrupted:
                raise InvalidStageTransitionError(
                    f"Cannot promote strategy '{strategy_id}' to HOLDOUT: "
                    "Holdout governance storage is corrupted (GOVERNANCE_LOCKED)."
                )
            prereg = mgr.get_preregistration(evidence_bundle.holdout_preregistration_id)
            if not prereg:
                raise InvalidStageTransitionError(
                    f"Preregistration '{evidence_bundle.holdout_preregistration_id}' not found in holdout manager."
                )
            if prereg.status not in (HoldoutStatus.PREREGISTERED, HoldoutStatus.UNOPENED):
                raise InvalidStageTransitionError(
                    f"Cannot promote to HOLDOUT: holdout preregistration is already {prereg.status.value}. "
                    "Holdout must remain unopened during promotion."
                )
            if (strategy_id, prereg.dataset_fingerprint) in mgr._burned_lineages:
                raise InvalidStageTransitionError(
                    f"Cannot promote to HOLDOUT: dataset fingerprint '{prereg.dataset_fingerprint}' for strategy "
                    f"'{strategy_id}' has already been accessed or burned."
                )
            if (
                prereg.strategy_id != strategy_id
                or prereg.strategy_version != evidence_bundle.strategy_version
                or prereg.dataset_fingerprint != evidence_bundle.dataset_fingerprint
                or prereg.config_fingerprint != evidence_bundle.config_fingerprint
                or prereg.parameter_set_fingerprint != evidence_bundle.parameter_set_fingerprint
                or prereg.git_sha != evidence_bundle.git_sha
            ):
                raise InvalidStageTransitionError(
                    "Provenance mismatch between holdout preregistration and promotion evidence bundle."
                )

        # 3. HOLDOUT -> PAPER requires verified PromotionEvidenceBundle with valid gate bundle, holdout evaluation, holdout_manager, and gate_store
        elif current_stage == StrategyStage.HOLDOUT and new_stage == StrategyStage.PAPER:
            if evidence_bundle is None:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition from HOLDOUT to PAPER: "
                    "PromotionEvidenceBundle is required."
                )
            if not evidence_bundle.holdout_preregistration_id or not evidence_bundle.holdout_access_id or not evidence_bundle.holdout_result_id:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition to PAPER: "
                    "Evidence bundle must contain holdout_preregistration_id, holdout_access_id, and holdout_result_id."
                )
            if mgr is None:
                raise InvalidStageTransitionError(
                    "HOLDOUT_GOVERNANCE_STORE_REQUIRED: Strategy cannot transition from HOLDOUT to PAPER without authoritative holdout_manager."
                )
            if mgr.is_corrupted:
                raise InvalidStageTransitionError(
                    f"Cannot promote strategy '{strategy_id}' to PAPER: "
                    "Holdout governance storage is corrupted (GOVERNANCE_LOCKED)."
                )
            prereg = mgr.get_preregistration(evidence_bundle.holdout_preregistration_id)
            if not prereg:
                raise InvalidStageTransitionError(f"Preregistration '{evidence_bundle.holdout_preregistration_id}' not found.")
            acc = mgr.get_access_record(evidence_bundle.holdout_access_id)
            if not acc:
                raise InvalidStageTransitionError(f"Access record '{evidence_bundle.holdout_access_id}' not found.")
            eval_res = mgr.get_evaluation_result(evidence_bundle.holdout_result_id)
            if not eval_res:
                raise InvalidStageTransitionError(f"Evaluation result '{evidence_bundle.holdout_result_id}' not found.")

            # Linking check
            if acc.preregistration_id != prereg.preregistration_id:
                raise InvalidStageTransitionError(
                    f"Holdout access record '{acc.access_id}' links to preregistration '{acc.preregistration_id}', "
                    f"expected '{prereg.preregistration_id}'."
                )
            if eval_res.preregistration_id != prereg.preregistration_id:
                raise InvalidStageTransitionError(
                    f"Holdout evaluation result '{eval_res.result_id}' links to preregistration '{eval_res.preregistration_id}', "
                    f"expected '{prereg.preregistration_id}'."
                )
            if eval_res.access_id != acc.access_id:
                raise InvalidStageTransitionError(
                    f"Holdout evaluation result '{eval_res.result_id}' links to access record '{eval_res.access_id}', "
                    f"expected '{acc.access_id}'."
                )

            # Full provenance check across artifacts
            for art_name, art in (("preregistration", prereg), ("access_record", acc), ("evaluation_result", eval_res)):
                if (
                    art.strategy_id != strategy_id
                    or art.strategy_version != evidence_bundle.strategy_version
                    or art.dataset_fingerprint != evidence_bundle.dataset_fingerprint
                    or art.config_fingerprint != evidence_bundle.config_fingerprint
                    or art.git_sha != evidence_bundle.git_sha
                ):
                    raise InvalidStageTransitionError(
                        f"Provenance mismatch between holdout {art_name} and promotion evidence bundle."
                    )
            if prereg.parameter_set_fingerprint != evidence_bundle.parameter_set_fingerprint or acc.parameter_set_fingerprint != evidence_bundle.parameter_set_fingerprint:
                raise InvalidStageTransitionError(
                    "Parameter set fingerprint mismatch across holdout artifacts and promotion evidence bundle."
                )

            if not eval_res.passed:
                raise InvalidStageTransitionError(f"Holdout evaluation result did not pass: {eval_res.reasons}.")

            # If evidence_bundle.gate_bundle is supplied, validate it first
            if evidence_bundle.gate_bundle:
                is_valid, reasons = validate_gate_bundle(evidence_bundle.gate_bundle)
                if not is_valid:
                    raise InvalidStageTransitionError(
                        f"Strategy '{strategy_id}' cannot transition to PAPER: "
                        f"Gate bundle failed strict validation: {reasons}"
                    )
                gate_list = list(evidence_bundle.gate_bundle.values()) if isinstance(evidence_bundle.gate_bundle, dict) else list(evidence_bundle.gate_bundle)
                first_gate = gate_list[0]
                if (
                    first_gate.strategy_id != strategy_id
                    or first_gate.dataset_fingerprint != evidence_bundle.dataset_fingerprint
                    or first_gate.config_fingerprint != evidence_bundle.config_fingerprint
                ):
                    raise InvalidStageTransitionError(
                        "Provenance mismatch between Gate Bundle and PromotionEvidenceBundle."
                    )

            # Authoritative Gate Evidence Store verification
            if store is None:
                raise InvalidStageTransitionError(
                    "GATE_EVIDENCE_STORE_REQUIRED: Strategy cannot transition from HOLDOUT to PAPER without authoritative gate_store."
                )
            if getattr(store, "is_corrupted", False):
                raise InvalidStageTransitionError(
                    f"Cannot promote strategy '{strategy_id}' to PAPER: "
                    "Gate evidence storage is corrupted (GOVERNANCE_LOCKED)."
                )
            if not evidence_bundle.gate_bundle_id:
                raise InvalidStageTransitionError(
                    f"Strategy '{strategy_id}' cannot transition to PAPER: "
                    "Evidence bundle must contain gate_bundle_id referencing authoritative GateEvaluationStore."
                )
            bundle_artifact = store.get_gate_bundle(evidence_bundle.gate_bundle_id)
            if not bundle_artifact:
                raise InvalidStageTransitionError(
                    f"Gate bundle '{evidence_bundle.gate_bundle_id}' not found in gate evidence store."
                )
            if bundle_artifact.status != "VERIFIED":
                raise InvalidStageTransitionError(
                    f"Gate bundle '{evidence_bundle.gate_bundle_id}' has status '{bundle_artifact.status}', expected 'VERIFIED'."
                )

            # Provenance match between bundle artifact and promotion evidence bundle
            if (
                bundle_artifact.strategy_id != strategy_id
                or bundle_artifact.strategy_version != evidence_bundle.strategy_version
                or bundle_artifact.dataset_fingerprint != evidence_bundle.dataset_fingerprint
                or bundle_artifact.config_fingerprint != evidence_bundle.config_fingerprint
                or bundle_artifact.parameter_set_fingerprint != evidence_bundle.parameter_set_fingerprint
                or bundle_artifact.git_sha != evidence_bundle.git_sha
            ):
                raise InvalidStageTransitionError(
                    "Provenance mismatch between GateBundleArtifact and PromotionEvidenceBundle."
                )

            # Verify all 4 gate records exist and passed
            for letter in ("A", "B", "C", "D"):
                ev_id = bundle_artifact.gate_evidence_ids.get(letter)
                if not ev_id:
                    raise InvalidStageTransitionError(
                        f"GateBundleArtifact missing canonical Gate {letter} in gate_evidence_ids."
                    )
                rec = store.get_gate_evaluation(ev_id)
                if not rec:
                    raise InvalidStageTransitionError(
                        f"Gate {letter} evidence record '{ev_id}' not found in gate store."
                    )
                if rec.gate_result.status != GateStatus.PASS:
                    raise InvalidStageTransitionError(
                        f"Gate {letter} evidence record has status '{rec.gate_result.status.value}', expected PASS."
                    )

        # 4. Transitions to SMALL_LIVE or ACTIVE are permanently BLOCKED under USD 0 live capital invariant
        elif new_stage in (StrategyStage.SMALL_LIVE, StrategyStage.ACTIVE):
            raise InvalidStageTransitionError(
                f"Strategy '{strategy_id}' cannot transition to {new_stage.value}: "
                "Authorized live capital is USD 0. Real order routing is permanently disabled."
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
    registry.register(get_seed_str_001(), trusted_seed=True)
    registry.register(get_seed_str_002(), trusted_seed=True)
    return registry


def create_extended_registry() -> StrategyRegistry:
    """Factory creating a StrategyRegistry populated with all standard seed research programs including v1.4 additions."""
    registry = create_default_registry()
    registry.register(get_seed_str_003(), trusted_seed=True)
    registry.register(get_seed_pump_fun_copy(), trusted_seed=True)
    return registry
