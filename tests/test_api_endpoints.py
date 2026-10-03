"""Integration tests for FastAPI Quant Cockpit API endpoints.

Validates core OS invariants exposed to the operational UI:
1. Live capital is strictly $0 and LOCKED.
2. Recorder status reflects real background process and manifest.
3. 24h & 72h gates never display PASS prematurely.
4. Strategy registry reflects seed candidates (STR-001, STR-002 v2, STR-003, STR-PUMP-COPY).
5. STR-002 economic edge is explicitly NOT VALIDATED.
6. Tradability distinguishes Tier 5 SMALL TRADABLE from UNTRADABLE.
7. PropRuleProfile unknown fields stay UNKNOWN and PENDING.
8. Prop exam simulator fails closed when empirical samples < 30 trades.
9. Holdout audits remain SEALED.
10. Paper account reflects simulated ledger with maker/taker fees and slippage.
"""

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "LOCKED" in data["live_capital_authorized"]


def test_system_status_live_capital_locked():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["live_capital_state"] == "LOCKED"
    assert data["authorized_live_capital_usd"] == 0.0
    assert data["live_trading_locked"] is True
    assert data["risk_state"] == "CAPITAL_LOCKED"
    assert data["strategies_total"] >= 4
    # Check gate durations
    assert data["gate_24h"]["status"] in ("PENDING", "READY")
    assert data["gate_24h"]["passed"] is False
    assert data["gate_72h"]["status"] in ("PENDING", "READY")
    assert data["gate_72h"]["passed"] is False


def test_system_git_and_ci():
    res_git = client.get("/api/system/git")
    assert res_git.status_code == 200
    assert res_git.json()["status"] == "AVAILABLE"
    assert len(res_git.json()["git_sha"]) == 40

    res_ci = client.get("/api/system/ci")
    assert res_ci.status_code == 200
    ci_data = res_ci.json()
    # No hardcoded counts: unverified CI/test results must be reported as UNKNOWN (None), never PASS/0.
    assert ci_data["passing_tests"] is None
    assert ci_data["failing_tests"] is None
    assert ci_data["status"] == "UNKNOWN"
    assert "UNKNOWN" in ci_data["github_actions_status"]


def test_recorder_status():
    res = client.get("/api/recorder/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "venues" in data
    assert "binance_perp" in data["venues"]
    assert "deribit" in data["venues"]
    assert "polymarket" in data["venues"]
    assert "bybit" in data["venues"]
    # Bybit is pending integration
    assert data["venues"]["bybit"]["status"] == "ADAPTER_READY_INTEGRATION_PENDING"
    # Gate progress bars never show PASS prematurely
    assert data["progress_24h_pct"] <= 100.0


def test_data_quality():
    res = client.get("/api/data-quality")
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "AVAILABLE":
        assert "storage_metrics" in data
        assert "timestamp_integrity" in data
        assert "gates" in data


def test_markets_tradability_tiers():
    res = client.get("/api/markets/tradability")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AVAILABLE"
    markets = {m["symbol"]: m for m in data["markets"]}

    # BTCUSDT is Tier 1 and tradable
    assert markets["BTCUSDT"]["tier_code"] == 1
    assert markets["BTCUSDT"]["tradable"] is True

    # SUIUSDT is Tier 5 SMALL TRADABLE with size limit and limit orders only
    assert markets["SUIUSDT"]["tier_code"] == 5
    assert markets["SUIUSDT"]["tradable"] is True
    assert markets["SUIUSDT"]["max_position_usd"] == 5000.0
    assert markets["SUIUSDT"]["limit_orders_only"] is True

    # ILLIQUID_ALT fails spread and is UNTRADABLE
    assert markets["ILLIQUID_ALT"]["tier_code"] == 6
    assert markets["ILLIQUID_ALT"]["tradable"] is False
    assert len(markets["ILLIQUID_ALT"]["rejection_reasons"]) > 0

    # SKEWED_FEED fails clock skew and is UNTRADABLE
    assert markets["SKEWED_FEED"]["tier_code"] == 6
    assert markets["SKEWED_FEED"]["tradable"] is False


def test_strategies_registry():
    res = client.get("/api/strategies")
    assert res.status_code == 200
    strats = {s["strategy_id"]: s for s in res.json()}

    # All seed strategies present
    assert "STR-001" in strats
    assert "STR-002" in strats
    assert "STR-003" in strats
    assert "STR-PUMP-COPY" in strats

    # Invariants on privilege
    for s in strats.values():
        assert s["is_privileged"] is False
        assert s["live_eligibility"] is False

    # STR-002 v2 specifics
    str002 = strats["STR-002"]
    assert str002["economic_edge_validated"] is False
    assert str002["economic_edge_status"] == "NOT VALIDATED"
    assert str002["execution_mode"] == "LONG_ONLY"


def test_strategy_detail_and_thesis():
    res = client.get("/api/strategies/STR-002")
    assert res.status_code == 200
    data = res.json()
    assert data["strategy_id"] == "STR-002"
    thesis = data["counterparty_thesis"]
    assert thesis is not None
    assert len(thesis["falsification_conditions"]) > 0
    assert thesis["is_complete_for_validation"] is True
    # Rules hierarchy
    assert len(data["rules_evidence"]) >= 5
    for r in data["rules_evidence"]:
        assert r["status"] == "INTUITION_UNVALIDATED"


def test_str002_specialized_view():
    res = client.get("/api/strategies/str002/specialized")
    assert res.status_code == 200
    data = res.json()
    assert data["strategy_id"] == "STR-002"
    assert data["execution_mode"] == "LONG_ONLY"
    assert data["economic_edge_status"] == "NOT VALIDATED"

    # Models M0 through M7 present
    variants = {v["variant_id"]: v for v in data["model_variants"]}
    for m_id in ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]:
        assert m_id in variants
        assert variants[m_id]["status"] == "UNVALIDATED"

    # Decision Matrix present
    matrix_states = [row["state"] for row in data["btc_decision_matrix"]]
    assert "FLAT" in matrix_states
    assert "UP" in matrix_states
    assert "DOWN" in matrix_states
    assert "RUNNING_HARD_DOWN" in matrix_states


def test_portfolio_selection_gates():
    res = client.get("/api/gates")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AVAILABLE"
    gates = {g["gate_id"]: g for g in data["gates"]}
    assert "A" in gates  # Latency
    assert "B" in gates  # Temporal
    assert "C" in gates  # Multiple Selection
    assert "D" in gates  # Correlation & Capacity
    for g in gates.values():
        assert g["threshold_is_provisional"] is True
        assert g["evaluation_status"] == "PENDING"


def test_portfolio_state_allocation():
    res = client.get("/api/portfolio")
    assert res.status_code == 200
    data = res.json()
    assert data["live_capital_state"] == "LOCKED"
    assert data["authorized_live_capital_usd"] == 0.0
    for alloc in data["allocations"]:
        assert alloc["authorized_live_budget"] == 0.0
        assert alloc["is_live_eligible"] is False


def test_paper_account_positions_and_orders():
    res = client.get("/api/paper/account")
    assert res.status_code == 200
    data = res.json()
    assert data["initial_cash_usd"] == 100_000.0
    assert data["simulated_latency_ms"] == 20.0
    assert "positions" in data
    assert "orders" in data
    assert "fills" in data


def test_risk_status_and_kill_switches():
    res = client.get("/api/risk/status")
    assert res.status_code == 200
    data = res.json()
    assert data["live_capital_state"] == "CAPITAL_LOCKED"
    assert data["authorized_live_capital_usd"] == 0.0
    assert "kill_switches" in data
    assert "GLOBAL" in data["kill_switches"]
    assert "OWN_POCKET" in data["kill_switches"]
    assert "PROP_POCKET" in data["kill_switches"]


def test_capital_pockets_isolation():
    res = client.get("/api/capital-pockets")
    assert res.status_code == 200
    data = res.json()
    assert "Zero risk transfer" in data["isolation_invariant"]
    pockets = {p["pocket_id"]: p for p in data["pockets"]}
    assert "OWN_MAIN" in pockets
    assert "PROP_ALPHA_100K" in pockets
    assert pockets["OWN_MAIN"]["pocket_type"] == "OWN"
    assert pockets["PROP_ALPHA_100K"]["pocket_type"] == "PROP"


def test_prop_profiles_and_unknown_fields():
    res = client.get("/api/prop/profiles")
    assert res.status_code == 200
    profiles = {p["provider_id"]: p for p in res.json()}

    # Verified profile
    assert "AlphaFunding" in profiles
    assert profiles["AlphaFunding"]["verification_status"] == "VERIFIED"

    # Unverified profile must retain UNKNOWN and PENDING per invariant
    assert "GammaProp" in profiles
    gamma = profiles["GammaProp"]
    assert gamma["verification_status"] == "PENDING"
    assert gamma["evaluation_execution"] == "UNKNOWN"
    assert gamma["payout_type"] == "UNKNOWN"
    assert gamma["api_bot_policy"] == "UNKNOWN"


def test_prop_simulator_fail_closed_on_insufficient_data():
    res = client.get("/api/prop/simulations?strategy_id=STR-002&provider_id=AlphaFunding")
    assert res.status_code == 200
    data = res.json()
    # Must return PENDING / INSUFFICIENT DATA because real trade sample < 30
    assert data["status"] == "PENDING / INSUFFICIENT_DATA"
    assert data["pass_probability"] == 0.0
    assert "Gaussian IID fallback strictly forbidden" in data["reason"]


def test_holdout_sealed():
    res = client.get("/api/holdouts")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("SEALED", "NOT_AVAILABLE")
    assert "HOLDOUT SEALED" in data["warning"]
