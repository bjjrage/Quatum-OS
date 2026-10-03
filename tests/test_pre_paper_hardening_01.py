"""Comprehensive adversarial unit and integration tests for Pre-Paper Backend Hardening 01.

Validates:
- Data Integrity (recorders, storage sink quarantine, manifest fail-closed)
- Risk Authority (input sanitization, in-flight tracking, missing mark prices, cross-account gross exposure)
- Paper Broker authorization by construction (SubmitPermit mandate)
- 24h/72h Gate fail-closed evaluation (liveness, data span, row count)
"""
import math
import time
from pathlib import Path
import pytest

from src.risk.engine import (
    DeterministicRiskEngine,
    ProposedOrder,
    RiskLimits,
    RiskViolationCode,
)
from src.risk.capital_pockets import (
    CapitalPocket,
    PocketType,
    MultiAccountRiskAggregator,
)
from src.paper.broker import (
    PaperBroker,
    PaperOrderSide,
    PaperOrderType,
)
from src.common.manifest import PartitionManifest, ManifestCorruptError
from src.common.storage_sink import StorageSink
from src.common.types import Venue
from src.quality.acceptance import (
    evaluate_duration_gate,
    MIN_24H_SECONDS,
)
from src.execution_plane.adapters.base import issue_permit
from src.execution_plane.models import ExecutionMode


# ==============================================================================
# 1. RISK ENGINE ADVERSARIAL TESTS (INPUT SANITIZATION & MARK PRICE FAIL-CLOSED)
# ==============================================================================

def test_risk_engine_rejects_nan_and_inf_inputs():
    """RiskEngine must strictly reject NaN, +Inf, -Inf in quantity or price."""
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)

    # NaN quantity
    nan_qty_order = ProposedOrder(
        order_id="ord-nan-qty",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=float("nan"),
        price=50_000.0,
    )
    dec = engine.evaluate_order(nan_qty_order)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.INVALID_ORDER
    assert "positive finite" in dec.reason

    # Inf price
    inf_price_order = ProposedOrder(
        order_id="ord-inf-p",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=1.0,
        price=float("inf"),
    )
    dec2 = engine.evaluate_order(inf_price_order)
    assert dec2.approved is False
    assert dec2.violation_code == RiskViolationCode.INVALID_ORDER


def test_risk_engine_rejects_invalid_side():
    """RiskEngine must strictly reject unrecognized sides like 'HOLD', 'CANCEL', None."""
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)

    hold_order = ProposedOrder(
        order_id="ord-hold",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="HOLD",
        quantity=1.0,
        price=50_000.0,
    )
    dec = engine.evaluate_order(hold_order)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.INVALID_ORDER
    assert "strictly 'BUY' or 'SELL'" in dec.reason


def test_risk_engine_zero_or_negative_equity_blocks_new_risk():
    """Zero, negative, or NaN equity must fail-closed and block any new risk-increasing order."""
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)
    engine.current_equity_usd = 0.0

    order = ProposedOrder(
        order_id="ord-zero-eq",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=50_000.0,
    )
    dec = engine.evaluate_order(order)
    assert dec.approved is False
    assert dec.violation_code in (RiskViolationCode.MAX_DRAWDOWN_EXCEEDED, RiskViolationCode.INVALID_ORDER)
    assert "non-positive" in dec.reason


def test_risk_engine_missing_mark_price_blocks_new_risk():
    """Holding open positions with missing or non-positive mark price must block new risk."""
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)
    # Open position of 1.0 BTC, but mark price is missing from mark_prices
    engine.positions = {"BTC-USDT": 1.0}
    engine.mark_prices = {}  # Empty mark prices

    order = ProposedOrder(
        order_id="ord-new-eth",
        strategy_id="STR-001",
        symbol="ETH-USDT",
        side="BUY",
        quantity=1.0,
        price=3_000.0,
    )
    dec = engine.evaluate_order(order)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.INVALID_ORDER
    assert "Missing or non-positive mark price" in dec.reason


# ==============================================================================
# 2. IN-FLIGHT ORDERS BURST PROTECTION
# ==============================================================================

def test_risk_engine_in_flight_orders_prevent_burst_limit_breach():
    """10 orders of $24,000 against a $25,000 cap must not all pass; in-flight tracking must reject order #2-10."""
    engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_single_position_pct=0.25),  # max $25,000
        auto_register_in_flight=True,
    )

    order1 = ProposedOrder(
        order_id="ord-burst-1",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.4,
        price=60_000.0,  # $24,000 notional <= $25,000 cap
    )
    dec1 = engine.evaluate_order(order1)
    assert dec1.approved is True
    assert "ord-burst-1" in engine.in_flight_orders

    # Second concurrent order before order 1 has filled:
    order2 = ProposedOrder(
        order_id="ord-burst-2",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.4,
        price=60_000.0,  # Another $24,000 brings pending exposure to $48,000 > $25,000 cap
    )
    dec2 = engine.evaluate_order(order2)
    assert dec2.approved is False
    assert dec2.violation_code == RiskViolationCode.SINGLE_ASSET_CONCENTRATION_EXCEEDED

    # Release order 1 (e.g. cancelled)
    engine.release_in_flight("ord-burst-1")
    dec2_retry = engine.evaluate_order(order2)
    assert dec2_retry.approved is True


# ==============================================================================
# 3. MULTI-ACCOUNT RISK AGGREGATOR (NO OPPOSITE POSITION NETTING)
# ==============================================================================

def test_multi_account_aggregator_does_not_net_opposite_positions():
    """Opposite positions (+600k in Acc A, -600k in Acc B) must yield $1.2M gross notional, NOT $0."""
    aggregator = MultiAccountRiskAggregator(
        max_global_gross_leverage=2.0,  # Max 2x leverage on $500k equity = $1.0M max gross
    )
    pocket_a = CapitalPocket(
        pocket_id="P_OWN",
        pocket_type=PocketType.OWN,
        account_id="ACC_A",
        initial_equity_usd=250_000.0,
        current_equity_usd=250_000.0,
        peak_equity_usd=250_000.0,
        daily_starting_equity_usd=250_000.0,
    )
    pocket_b = CapitalPocket(
        pocket_id="P_PROP",
        pocket_type=PocketType.PROP,
        account_id="ACC_B",
        initial_equity_usd=250_000.0,
        current_equity_usd=250_000.0,
        peak_equity_usd=250_000.0,
        daily_starting_equity_usd=250_000.0,
    )
    aggregator.add_pocket(pocket_a)
    aggregator.add_pocket(pocket_b)

    # Acc A has +10 BTC ($600k long), Acc B has -10 BTC ($600k short)
    aggregator.update_positions(
        account_id="ACC_A",
        positions={"BTCUSDT": 10.0},
        mark_prices={"BTCUSDT": 60_000.0},
    )
    aggregator.update_positions(
        account_id="ACC_B",
        positions={"BTCUSDT": -10.0},
        mark_prices={"BTCUSDT": 60_000.0},
    )

    # Net position across accounts is 0.0, BUT gross notional is $1,200,000!
    # On $500,000 equity, leverage is 2.4x > 2.0x ceiling -> must fail!
    approved, reason, metrics = aggregator.evaluate_global_risk()
    assert approved is False
    assert "Global gross leverage" in reason
    assert metrics["gross_notional"] == 1_200_000.0
    assert metrics["gross_leverage"] == 2.4


def test_multi_account_aggregator_frozen_pocket_blocks_order():
    """Frozen pocket must reject new risk-increasing orders."""
    aggregator = MultiAccountRiskAggregator()
    pocket = CapitalPocket(
        pocket_id="P_FROZEN",
        pocket_type=PocketType.PROP,
        account_id="ACC_FROZEN",
        initial_equity_usd=50_000.0,
        current_equity_usd=40_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
        is_frozen=True,
        freeze_reason="Daily loss limit breached",
    )
    aggregator.add_pocket(pocket)

    # Risk-increasing BUY order on frozen pocket -> reject
    ok, reason = aggregator.evaluate_pocket_order(
        pocket_id="P_FROZEN",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )
    assert ok is False
    assert "is frozen" in reason


# ==============================================================================
# 4. PAPER BROKER RISK PERMIT MANDATE (NO BYPASS BY CONSTRUCTION)
# ==============================================================================

def test_paper_broker_strictly_rejects_unpermitted_orders():
    """Direct submission to PaperBroker without an approved permit must raise PermissionError."""
    broker = PaperBroker()  # default enforce_risk_permit=True
    with pytest.raises(PermissionError, match="Pre-trade Risk permit is mandatory"):
        broker.submit_order(
            symbol="BTC-USDT",
            side=PaperOrderSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=0.5,
            current_bbo={"best_bid": 60_000.0, "best_ask": 60_010.0},
        )


def test_paper_broker_accepts_order_with_valid_risk_permit():
    """PaperBroker accepts order when authorized with a valid approved SubmitPermit."""
    broker = PaperBroker(simulated_latency_ms=0.0)
    permit = issue_permit(
        kind="SUBMIT",
        venue="paper",
        client_order_id="client_ord_999",
        mode=ExecutionMode.PAPER,
        authorized_live_capital_usd=0.0,
        risk_approved=True,
        issued_ns=1_000_000_000,
    )
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=0.5,
        current_bbo={"best_bid": 60_000.0, "best_ask": 60_010.0, "ask_size": 1.0, "bid_size": 1.0},
        permit=permit,
    )
    assert order.status.value == "FILLED"


# ==============================================================================
# 5. 24H/72H ACCEPTANCE GATE FAIL-CLOSED INTEGRITY
# ==============================================================================

def test_gate_duration_fails_if_process_is_dead_or_data_sparse():
    """Even if wall-clock elapsed >= 24h, dead process or sparse row counts must FAIL."""
    # Scenario: 80 hours elapsed, but recorder PID is dead
    res_dead_pid = evaluate_duration_gate(
        gate_name="24h",
        elapsed_seconds=MIN_24H_SECONDS + 5000.0,
        metrics_pass=True,
        is_process_alive=False,  # Dead PID
        total_row_count=50_000,
    )
    assert res_dead_pid.status == "FAIL"
    assert res_dead_pid.passed is False
    assert any("not alive" in r for r in res_dead_pid.reasons)

    # Scenario: 24h elapsed, PID alive, but only 10 rows recorded
    res_sparse = evaluate_duration_gate(
        gate_name="24h",
        elapsed_seconds=MIN_24H_SECONDS + 5000.0,
        metrics_pass=True,
        is_process_alive=True,
        total_row_count=10,  # 10 rows is unacceptable for 24h continuous recording
        min_row_count=5_000,
    )
    assert res_sparse.status == "FAIL"
    assert res_sparse.passed is False
    assert any("Insufficient data volume" in r for r in res_sparse.reasons)


# ==============================================================================
# 6. STORAGE SINK ATOMICITY & QUARANTINE INTEGRITY
# ==============================================================================

@pytest.mark.asyncio
async def test_storage_sink_quarantine_on_unhandled_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """StorageSink must dump unwriteable buffer to quarantine and track failed/quarantined counters."""
    import pyarrow.parquet as pq

    sink = StorageSink(base_path=tmp_path, flush_interval_sec=100.0)

    # Append valid event
    row = {
        "ts_exchange_ns": 1_000_000_000,
        "ts_received_utc_ns": 1_000_000_000,
        "ts_received_mono_ns": 1_000_000_000,
        "observed_event_age_ns": 0,
        "venue": "binance_perp",
        "symbol": "BTCUSDT",
        "trade_id": "t1",
        "side": "BUY",
        "price": 60_000.0,
        "size": 0.1,
    }
    await sink.append("binance_perp", "trade_ticks", row)
    assert sink.events_received == 1

    # Simulate parquet write failure by patching pq.write_table
    def broken_write(*args, **kwargs):
        raise IOError("Disk write simulation error")

    monkeypatch.setattr(pq, "write_table", broken_write)

    # Flushing should not crash the process; it should quarantine and increment failure counters
    await sink.flush_all()
    assert sink.events_failed == 1
    assert sink.events_quarantined == 1
    assert sink.write_failures == 1
    assert "Disk write simulation error" in sink.last_write_error

    # Verify quarantine file exists on disk
    quarantine_files = list(tmp_path.glob("quarantine/**/*.json"))
    assert len(quarantine_files) >= 1


def test_manifest_corruption_raises_fail_closed_error(tmp_path: Path):
    """Corrupted manifest file must raise ManifestCorruptError rather than returning partial/empty state."""
    partition_dir = tmp_path / "binance_perp" / "table=trade_ticks" / "year=2026" / "month=10" / "day=03" / "hour=01"
    partition_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = partition_dir / "manifest.json"

    # Write corrupt JSON bytes
    manifest_path.write_text('{"parts": [{"part_filename": "part-1.parquet", "incomplete": ', encoding="utf-8")

    manifest = PartitionManifest(partition_dir)
    with pytest.raises(ManifestCorruptError, match="corrupted"):
        manifest._read_manifest()
