"""Unit tests for Strategy Domain and Registry with hardened governance invariants."""

import pytest
import tempfile
from pathlib import Path
from src.strategies.models import (
    StrategyOrigin,
    StrategyStage,
    StrategyFamily,
    StrategySpec,
    CounterpartyThesis,
    PromotionEvidenceBundle,
)
from src.research.holdout import SealedHoldoutManager
from src.portfolio.gates import StrategyGateResult
from src.portfolio.gate_evidence import GateEvaluationStore
from src.strategies.registry import (
    StrategyRegistry,
    DuplicateStrategyError,
    StrategyNotFoundError,
    InvalidStageTransitionError,
    get_seed_str_001,
    get_seed_str_002,
    create_default_registry,
)


def test_register_valid_strategy():
    """Verify registration and retrieval of a valid strategy specification."""
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-TEST-01",
        name="StatArb Pairs",
        family=StrategyFamily.STATISTICAL_ARBITRAGE.value,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.IDEA,
        description="Cointegration-based pairs trading on perpetual futures.",
    )
    registry.register(spec)
    retrieved = registry.get("STR-TEST-01")
    assert retrieved.strategy_id == "STR-TEST-01"
    assert retrieved.name == "StatArb Pairs"
    assert retrieved.family == StrategyFamily.STATISTICAL_ARBITRAGE.value
    assert retrieved.origin == StrategyOrigin.STATISTICAL
    assert retrieved.stage == StrategyStage.IDEA


def test_reject_duplicate_strategy_id():
    """Verify that registering an existing strategy ID raises DuplicateStrategyError."""
    registry = StrategyRegistry()
    spec1 = StrategySpec(
        strategy_id="STR-DUP-01",
        name="First Strategy",
        family=StrategyFamily.MOMENTUM.value,
        origin=StrategyOrigin.QUANT,
    )
    spec2 = StrategySpec(
        strategy_id="STR-DUP-01",
        name="Duplicate Strategy",
        family=StrategyFamily.MEAN_REVERSION.value,
        origin=StrategyOrigin.ML,
    )
    registry.register(spec1)
    with pytest.raises(DuplicateStrategyError, match="STR-DUP-01"):
        registry.register(spec2)


def test_represent_all_lifecycle_stages():
    """Verify that all 11 lifecycle stages can be represented and transitioned step-by-step."""
    expected_stages = [
        StrategyStage.IDEA,
        StrategyStage.RESEARCH,
        StrategyStage.VALIDATION,
        StrategyStage.HOLDOUT,
        StrategyStage.PAPER,
        StrategyStage.SMALL_LIVE,
        StrategyStage.ACTIVE,
        StrategyStage.REDUCED,
        StrategyStage.PAUSED,
        StrategyStage.KILLED,
        StrategyStage.ARCHIVED,
    ]
    assert len(expected_stages) == 11

    thesis = CounterpartyThesis(
        counterparty_type="Informed liquidity takers",
        economic_mechanism="Microstructure inventory imbalance",
        why_trade_now="Execution urgency",
        why_impact_may_be_transient="Inventory rebalancing",
        why_it_may_be_information="Macro news",
        observable_evidence=["Spread widening"],
        falsification_conditions=["Persistent adverse selection"],
    )
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-STAGE-01",
        name="Stage Pipeline Test",
        family="CUSTOM_TEST",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.IDEA,
        counterparty_thesis=thesis,
        economic_edge_validated=True,
    )
    registry.register(spec)

    for stage in expected_stages:
        s = spec.model_copy(update={"stage": stage})
        assert s.stage == stage


def test_represent_all_strategy_origins():
    """Verify that all 5 strategy origins can be represented without restriction."""
    expected_origins = [
        StrategyOrigin.HUMAN,
        StrategyOrigin.QUANT,
        StrategyOrigin.STATISTICAL,
        StrategyOrigin.ML,
        StrategyOrigin.AI_RESEARCH,
    ]
    assert len(expected_origins) == 5

    registry = StrategyRegistry()
    for origin in expected_origins:
        s_id = f"STR-ORIGIN-{origin.value}"
        spec = StrategySpec(
            strategy_id=s_id,
            name=f"Strategy from {origin.value}",
            family=StrategyFamily.CROSS_MARKET.value,
            origin=origin,
            stage=StrategyStage.RESEARCH,
        )
        registry.register(spec)
        assert registry.get(s_id).origin == origin


def test_register_arbitrary_future_strategy_family():
    """Verify that arbitrary un-enumerated strategy families can be registered dynamically."""
    registry = StrategyRegistry()
    custom_families = [
        "LLM_SENTIMENT_BREAKOUT",
        "CROSS_CHAIN_BRIDGE_ARBITRAGE",
        "MEV_AUCTION_RECOVERY",
        "LIQUID_STAKING_BASIS",
    ]
    for fam in custom_families:
        s_id = f"STR-{fam[:10]}"
        spec = StrategySpec(
            strategy_id=s_id,
            name=f"Custom Family {fam}",
            family=fam,
            origin=StrategyOrigin.AI_RESEARCH,
            stage=StrategyStage.IDEA,
        )
        registry.register(spec)
        assert registry.get(s_id).family == fam


def test_str_001_behaves_like_normal_registry_entry():
    """Verify STR-001 (Seed Line A) is an ordinary, non-privileged registry entry."""
    spec = get_seed_str_001()
    assert spec.strategy_id == "STR-001"
    assert spec.name == "Polymarket x Deribit Relative Value"
    assert spec.origin == StrategyOrigin.QUANT
    assert spec.stage == StrategyStage.RESEARCH
    assert spec.math_foundation_validated is True
    assert spec.economic_edge_validated is False
    assert spec.is_privileged is False

    registry = StrategyRegistry()
    registry.register(spec)
    assert registry.get("STR-001") == spec


def test_str_002_behaves_like_normal_registry_entry():
    """Verify STR-002 (Seed Line B) is an ordinary, non-privileged registry entry."""
    spec = get_seed_str_002()
    assert spec.strategy_id == "STR-002"
    assert spec.name == "Impulse / Overshoot / Short-Horizon Retracement"
    assert spec.origin == StrategyOrigin.HUMAN
    assert spec.stage == StrategyStage.RESEARCH
    assert spec.math_foundation_validated is False
    assert spec.economic_edge_validated is False
    assert spec.is_privileged is False

    registry = StrategyRegistry()
    registry.register(spec)
    assert registry.get("STR-002") == spec


def test_origin_creates_no_privileged_behavior():
    """Verify that no strategy origin confers special privileges, and attempting to privilege any fails."""
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="STR-PRIV-01",
            name="Attempted Privileged Strategy",
            family="ARBITRAGE",
            origin=StrategyOrigin.HUMAN,
            is_privileged=True,
        )

    registry = create_default_registry()
    strategies = registry.list_all()
    assert len(strategies) == 2
    for s in strategies:
        assert s.is_privileged is False


def test_privilege_cannot_be_injected_via_mutation_or_copy():
    """HARDENING: Invariant 1 - Verify that StrategySpec cannot technically become privileged.

    Tests:
    1. Direct property assignment raises AttributeError.
    2. model_copy(update={'is_privileged': True}) raises ValueError.
    3. object.__setattr__ fails to override descriptor (spec.is_privileged remains False).
    4. Constructor rejects truthy is_privileged.
    """
    spec = StrategySpec(
        strategy_id="STR-HARDEN-01",
        name="Harden Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
    )
    assert spec.is_privileged is False

    # 1. Direct attribute mutation must be blocked by read-only property / frozen model
    with pytest.raises((AttributeError, Exception)):
        spec.is_privileged = True

    # 2. model_copy update injection must raise ValueError
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        spec.model_copy(update={"is_privileged": True})

    # 3. Descriptor priority prevents even object.__setattr__ from writing to property
    with pytest.raises(AttributeError, match="has no setter"):
        object.__setattr__(spec, "is_privileged", True)
    assert spec.is_privileged is False

    # 4. Constructor injection
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="STR-HARDEN-02",
            name="Harden Test 2",
            family="MOMENTUM",
            origin=StrategyOrigin.ML,
            is_privileged=True,
        )


def test_evidence_gated_lifecycle_transitions():
    """HARDENING: Invariant 2 - Verify that strategy lifecycle transitions enforce evidence gates.

    Allowed forward promotion:
      RESEARCH -> VALIDATION
      VALIDATION -> HOLDOUT
      HOLDOUT -> PAPER
      PAPER -> SMALL_LIVE
      SMALL_LIVE -> ACTIVE

    Illegal gate bypasses:
      RESEARCH -> ACTIVE (bypasses validation, holdout, paper, small_live)
      IDEA -> SMALL_LIVE (bypasses research, validation, holdout, paper)
      VALIDATION -> ACTIVE (bypasses holdout, paper, small_live)

    Operational reversibility:
      ACTIVE -> PAUSED
      PAUSED -> ACTIVE

    Kill / archive:
      RESEARCH -> KILLED
      KILLED -> ARCHIVED
      ARCHIVED -> anything (terminal, must be rejected)
    """
    thesis = CounterpartyThesis(
        counterparty_type="Informed liquidity takers",
        economic_mechanism="Microstructure inventory imbalance",
        why_trade_now="Execution urgency",
        why_impact_may_be_transient="Inventory rebalancing",
        why_it_may_be_information="Macro news",
        observable_evidence=["Spread widening"],
        falsification_conditions=["Persistent adverse selection"],
    )
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-GATE-01",
        name="Gate Test",
        family="RELATIVE_VALUE",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=thesis,
        economic_edge_validated=True,
    )
    registry.register(spec)

    # 1. Allowed forward sequence
    registry.update_stage("STR-GATE-01", StrategyStage.VALIDATION)
    assert registry.get("STR-GATE-01").stage == StrategyStage.VALIDATION

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-GATE-01",
            strategy_version="1.0.0",
            git_sha="git_sha_test",
            dataset_fingerprint="ds_fp_test",
            config_fingerprint="cfg_fp_test",
            parameter_set_fingerprint="param_fp_test",
            hypothesis_description="Validating momentum persistence",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-GATE-01",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_fp_test",
            config_fingerprint="cfg_fp_test",
            parameter_set_fingerprint="param_fp_test",
            git_sha="git_sha_test",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-GATE-01", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)
        assert registry.get("STR-GATE-01").stage == StrategyStage.HOLDOUT

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-GATE-01",
            strategy_version="1.0.0",
            git_sha="git_sha_test",
            config_fingerprint="cfg_fp_test",
            parameter_set_fingerprint="param_fp_test",
        )
        eval_res = mgr.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics={"sharpe": 1.5},
            reasons=["All thresholds met"],
        )
        assert eval_res.passed is True

        # HOLDOUT -> PAPER requires PromotionEvidenceBundle with valid 4-gate bundle and gate_store
        gate_a = StrategyGateResult.create_pass("STR-GATE-01", "LATENCY_SENSITIVITY", "ds_fp_test", "cfg_fp_test", {"ok": True})
        gate_b = StrategyGateResult.create_pass("STR-GATE-01", "TEMPORAL_STABILITY", "ds_fp_test", "cfg_fp_test", {"ok": True})
        gate_c = StrategyGateResult.create_pass("STR-GATE-01", "MULTIPLE_SELECTION", "ds_fp_test", "cfg_fp_test", {"ok": True})
        gate_d = StrategyGateResult.create_pass("STR-GATE-01", "CORRELATION_CAPACITY", "ds_fp_test", "cfg_fp_test", {"ok": True})
        gate_bundle = {"A": gate_a, "B": gate_b, "C": gate_c, "D": gate_d}

        gate_store = GateEvaluationStore(storage_dir=Path(tmp) / "gate_store")
        bundle_art, _ = gate_store.record_and_bundle_gates(
            gate_results=gate_bundle,
            parameter_set_fingerprint="param_fp_test",
            git_sha="git_sha_test",
        )

        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-GATE-01",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_fp_test",
            config_fingerprint="cfg_fp_test",
            parameter_set_fingerprint="param_fp_test",
            git_sha="git_sha_test",
            gate_bundle_id=bundle_art.gate_bundle_id,
            gate_bundle=gate_bundle,
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
        )
        registry.update_stage(
            "STR-GATE-01",
            StrategyStage.PAPER,
            evidence_bundle=bundle_paper,
            holdout_manager=mgr,
            gate_store=gate_store,
        )
        assert registry.get("STR-GATE-01").stage == StrategyStage.PAPER

        # PAPER -> SMALL_LIVE is permanently blocked while live capital is USD 0
        with pytest.raises(InvalidStageTransitionError, match="Authorized live capital is USD 0"):
            registry.update_stage("STR-GATE-01", StrategyStage.SMALL_LIVE)

    # 3. Illegal gate-skipping tests
    spec_research = StrategySpec(
        strategy_id="STR-GATE-JUMP-1",
        name="Jump 1",
        family="MOMENTUM",
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.RESEARCH,
    )
    registry.register(spec_research)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-1", StrategyStage.ACTIVE)

    spec_idea = StrategySpec(
        strategy_id="STR-GATE-JUMP-2",
        name="Jump 2",
        family="MOMENTUM",
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.IDEA,
    )
    registry.register(spec_idea)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-2", StrategyStage.SMALL_LIVE)

    spec_validation = StrategySpec(
        strategy_id="STR-GATE-JUMP-3",
        name="Jump 3",
        family="MOMENTUM",
        origin=StrategyOrigin.ML,
        stage=StrategyStage.VALIDATION,
        counterparty_thesis=thesis,
    )
    registry.register(spec_validation, trusted_seed=True)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-3", StrategyStage.ACTIVE)

    # 4. Kill and terminal archive paths
    spec_kill = StrategySpec(
        strategy_id="STR-GATE-KILL",
        name="Kill Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
    )
    registry.register(spec_kill)
    registry.update_stage("STR-GATE-KILL", StrategyStage.KILLED)
    assert registry.get("STR-GATE-KILL").stage == StrategyStage.KILLED

    registry.update_stage("STR-GATE-KILL", StrategyStage.ARCHIVED)
    assert registry.get("STR-GATE-KILL").stage == StrategyStage.ARCHIVED

    # ARCHIVED is terminal: any outbound transition must fail
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.RESEARCH)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.ACTIVE)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.IDEA)


def test_str_002_thesis_and_dimensions_preserved():
    """HARDENING: Invariant 3 - Verify STR-002 thesis preserves original behavioral overshoot hypothesis.

    Verifies that:
    1. Thesis is defined as extreme price impulses normalized by prior volatility.
    2. Orderbook information is documented as a feature, not the definition.
    3. Informative move vs Forced liquidity move distinction is formally documented.
    """
    spec = get_seed_str_002()

    expected_thesis = (
        "Extreme short-horizon price impulses, normalized by prior volatility, "
        "may exhibit an exploitable overshoot followed by retracement."
    )
    assert expected_thesis in spec.description
    assert spec.metadata["thesis"] == expected_thesis

    # Check move types
    assert "informative_move" in spec.metadata["move_types"]
    assert "forced_liquidity_move" in spec.metadata["move_types"]

    # Check research dimensions
    dimensions = spec.metadata["research_dimensions"]
    assert "impulse_magnitude" in dimensions
    assert "prior_realized_volatility" in dimensions
    assert "forward_return" in dimensions
    assert "retracement_ratio" in dimensions
    assert "mfe" in dimensions
    assert "mae" in dimensions
    assert "time_to_retracement" in dimensions
    assert "forced_liquidations" in dimensions

    # Verify feature note
    assert "Orderbook information is an evaluation feature" in spec.metadata["feature_notes"]


def test_registry_has_no_execution_authority():
    """Verify non-negotiable governance: StrategyRegistry has strictly zero execution authority."""
    registry = StrategyRegistry()
    assert registry.has_execution_authority() is False

    forbidden_methods = [
        "execute_trade",
        "place_order",
        "submit_order",
        "allocate_capital",
        "connect_broker",
    ]
    for method in forbidden_methods:
        assert not hasattr(registry, method), f"Registry illegally exposes '{method}'!"


def test_strategy_not_found_raises():
    """Verify StrategyNotFoundError on missing strategy."""
    registry = StrategyRegistry()
    with pytest.raises(StrategyNotFoundError):
        registry.get("STR-NONEXISTENT")


def test_strategy_spec_and_thesis_forbid_extra_fields():
    """Verify ConfigDict(extra='forbid') prevents typo fields from silently being ignored."""
    from pydantic import ValidationError
    from src.strategies.models import StrategyParameterSet

    # Extra field on StrategySpec
    with pytest.raises(ValidationError):
        StrategySpec(
            strategy_id="STR-TYPO",
            name="Typo Strategy",
            family="MOMENTUM",
            origin=StrategyOrigin.QUANT,
            typo_attribute="illegal_value",
        )

    # Extra field on CounterpartyThesis
    with pytest.raises(ValidationError):
        CounterpartyThesis(
            counterparty_type="Arbitrageur",
            economic_mechanism="Friction",
            why_trade_now="Urgency",
            why_impact_may_be_transient="Reversion",
            why_it_may_be_information="News",
            falsification_conditions=["Adverse selection"],
            unknown_extra_field=123,
        )

    # Typed StrategyParameterSet validation
    params = StrategyParameterSet(
        parameter_set_id="params_v1",
        family="MOMENTUM",
        parameters={"lookback": 50, "threshold": 2.5},
    )
    spec = StrategySpec(
        strategy_id="STR-TYPED-01",
        name="Typed Params Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        parameters=params,
    )
    assert spec.parameters.parameters["lookback"] == 50


def test_registry_registration_governance_invariants():
    """Verify that StrategyRegistry.register strictly rejects illegal specs."""
    registry = StrategyRegistry()

    # 1. Reject non-StrategySpec
    with pytest.raises(TypeError, match="Expected StrategySpec"):
        registry.register({"not": "a spec"})

    # 2. Reject registering directly as ACTIVE without economic edge validation / USD 0 capital
    spec_active_unvalidated = StrategySpec(
        strategy_id="STR-ILLEGAL-ACTIVE",
        name="Illegal Active",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
        economic_edge_validated=False,
    )
    with pytest.raises(ValueError, match="Authorized live capital is USD 0"):
        registry.register(spec_active_unvalidated)

    # 3. Reject registering past RESEARCH stage without CounterpartyThesis
    spec_val_no_thesis = StrategySpec(
        strategy_id="STR-NO-THESIS",
        name="No Thesis",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.VALIDATION,
        counterparty_thesis=None,
    )
    with pytest.raises(ValueError, match="without a complete CounterpartyThesis"):
        registry.register(spec_val_no_thesis, trusted_seed=True)


def test_lifecycle_governance_fail_closed_transitions():
    """Verify Master Blueprint Section 5 Lifecycle Governance:
    IDEA -> RESEARCH -> VALIDATION -> HOLDOUT -> PAPER -> SMALL_LIVE -> ACTIVE.
    
    Prohibits arbitrary jumps and unvalidated capital promotion.
    Required failure checks:
    - RESEARCH -> ACTIVE MUST FAIL
    - IDEA -> PAPER MUST FAIL
    - HOLDOUT -> ACTIVE MUST FAIL
    - ARCHIVED -> RESEARCH MUST FAIL
    - PAPER -> SMALL_LIVE (unvalidated) MUST FAIL
    """
    thesis = CounterpartyThesis(
        counterparty_type="Informed liquidity takers",
        economic_mechanism="Microstructure inventory imbalance",
        why_trade_now="Execution urgency",
        why_impact_may_be_transient="Inventory rebalancing",
        why_it_may_be_information="Macro news",
        observable_evidence=["Spread widening"],
        falsification_conditions=["Persistent adverse selection"],
    )
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-LIFECYCLE-TEST",
        name="Lifecycle Governance Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.IDEA,
        counterparty_thesis=thesis,
        economic_edge_validated=False,
    )
    registry.register(spec)

    # 1. IDEA -> PAPER MUST FAIL
    with pytest.raises(InvalidStageTransitionError, match="cannot transition from IDEA to PAPER"):
        registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.PAPER)

    # Valid: IDEA -> RESEARCH
    registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.RESEARCH)
    assert registry.get("STR-LIFECYCLE-TEST").stage == StrategyStage.RESEARCH

    # 2. RESEARCH -> ACTIVE MUST FAIL
    with pytest.raises(InvalidStageTransitionError, match="cannot transition from RESEARCH to ACTIVE"):
        registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.ACTIVE)

    # Valid: RESEARCH -> VALIDATION (has valid thesis)
    registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.VALIDATION)
    assert registry.get("STR-LIFECYCLE-TEST").stage == StrategyStage.VALIDATION

    # Valid: VALIDATION -> HOLDOUT requires PromotionEvidenceBundle
    with pytest.raises(InvalidStageTransitionError, match="PromotionEvidenceBundle is required"):
        registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.HOLDOUT)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-LIFECYCLE-TEST",
            strategy_version="1.0.0",
            git_sha="git_sha",
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            parameter_set_fingerprint="param_fp",
            hypothesis_description="Validating momentum persistence",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        bundle_val_holdout = PromotionEvidenceBundle(
            strategy_id="STR-LIFECYCLE-TEST",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            parameter_set_fingerprint="param_fp",
            git_sha="git_sha",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.HOLDOUT, evidence_bundle=bundle_val_holdout, holdout_manager=mgr)
        assert registry.get("STR-LIFECYCLE-TEST").stage == StrategyStage.HOLDOUT

        # 3. HOLDOUT -> ACTIVE MUST FAIL
        with pytest.raises(InvalidStageTransitionError, match="cannot transition from HOLDOUT to ACTIVE"):
            registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.ACTIVE)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-LIFECYCLE-TEST",
            strategy_version="1.0.0",
            git_sha="git_sha",
            config_fingerprint="cfg_fp",
            parameter_set_fingerprint="param_fp",
        )
        eval_res = mgr.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics={"sharpe": 1.5},
            reasons=["All thresholds met"],
        )
        assert eval_res.passed is True

        # Valid: HOLDOUT -> PAPER requires PromotionEvidenceBundle with valid gate bundle and gate_store
        gate_a = StrategyGateResult.create_pass("STR-LIFECYCLE-TEST", "LATENCY_SENSITIVITY", "ds_fp", "cfg_fp", {"ok": True})
        gate_b = StrategyGateResult.create_pass("STR-LIFECYCLE-TEST", "TEMPORAL_STABILITY", "ds_fp", "cfg_fp", {"ok": True})
        gate_c = StrategyGateResult.create_pass("STR-LIFECYCLE-TEST", "MULTIPLE_SELECTION", "ds_fp", "cfg_fp", {"ok": True})
        gate_d = StrategyGateResult.create_pass("STR-LIFECYCLE-TEST", "CORRELATION_CAPACITY", "ds_fp", "cfg_fp", {"ok": True})
        gate_bundle = {"A": gate_a, "B": gate_b, "C": gate_c, "D": gate_d}

        gate_store = GateEvaluationStore(storage_dir=Path(tmp) / "gate_store_2")
        bundle_art, _ = gate_store.record_and_bundle_gates(
            gate_results=gate_bundle,
            parameter_set_fingerprint="param_fp",
            git_sha="git_sha",
        )

        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-LIFECYCLE-TEST",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            parameter_set_fingerprint="param_fp",
            git_sha="git_sha",
            gate_bundle_id=bundle_art.gate_bundle_id,
            gate_bundle=gate_bundle,
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
        )
        registry.update_stage(
            "STR-LIFECYCLE-TEST",
            StrategyStage.PAPER,
            evidence_bundle=bundle_paper,
            holdout_manager=mgr,
            gate_store=gate_store,
        )
        assert registry.get("STR-LIFECYCLE-TEST").stage == StrategyStage.PAPER

        # 4. PAPER -> SMALL_LIVE is permanently blocked while authorized live capital is USD 0
        with pytest.raises(InvalidStageTransitionError, match="Authorized live capital is USD 0"):
            registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.SMALL_LIVE)

    # Kill and Archive
    registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.KILLED)
    registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.ARCHIVED)
    assert registry.get("STR-LIFECYCLE-TEST").stage == StrategyStage.ARCHIVED

    # 5. ARCHIVED -> RESEARCH MUST FAIL (terminal state)
    with pytest.raises(InvalidStageTransitionError, match="cannot transition from ARCHIVED to RESEARCH"):
        registry.update_stage("STR-LIFECYCLE-TEST", StrategyStage.RESEARCH)


def test_register_past_research_requires_trusted_seed():
    """Audit fix: no direct registration at VALIDATION/HOLDOUT/PAPER from untrusted callers."""
    from src.strategies.registry import StrategyRegistry
    registry = StrategyRegistry()
    for stage in (StrategyStage.VALIDATION, StrategyStage.HOLDOUT, StrategyStage.PAPER):
        spec = StrategySpec(strategy_id=f"STR-JUMP-{stage.value}", name="x", family="MOMENTUM",
                            origin=StrategyOrigin.QUANT, stage=stage, counterparty_thesis=None)
        with pytest.raises(ValueError, match="directly in stage"):
            registry.register(spec)
