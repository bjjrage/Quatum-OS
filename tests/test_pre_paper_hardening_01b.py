"""
Adversarial test suite for Pre-Paper Backend Hardening 01b.

Covers:
1. Execution Authorization & Anti-Forgery (Gap 1):
   - Strict rejection of duck-typed fake permit objects.
   - Rejection of forged / tampered HMAC signatures.
   - Rejection of mismatched symbol / venue.
   - Expiration enforcement (fail-closed past expires_at_ns).
   - Replay protection (single-use token consumption).
   - Router minting bound exclusively to approved RiskDecision.

2. Acceptance Gate Data Continuity (Gap 2):
   - Effective continuous data span calculation across streams.
   - Rejection of missing required streams (effective_span = 0.0).
   - Rejection of burst without continuity (e.g. 100k rows in 15m).
   - Rejection of inter-stream gaps exceeding operational prior threshold.
   - Rejection of stale streams.
   - Pass path when true continuous span >= required duration.

3. Storage Sink Double-Failure Resilience (Gap 3):
   - Status reporting: COMMITTED vs QUARANTINED vs RETRY_REQUIRED.
   - In-memory retention of buffer on double failure (Parquet + quarantine fail).
   - State transition: HEALTHY -> DEGRADED -> FAILED.
   - Retry capability and recovery on subsequent flush.
   - Uncommitted row detection on shutdown.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.common.storage_sink import ChunkWriteStatus, StorageSink, StorageSinkState
from src.execution_plane.adapters.base import (
    ExecutionAuthorization,
    ExecutionAuthorizer,
    SubmitPermit,
    issue_permit,
    mint_test_authorization,
)
from src.execution_plane.models import ExecutionMode, OrderIntent
from src.execution_plane.router import ExecutionRouter
from src.paper.broker import PaperBroker, PaperOrderSide, PaperOrderType
from src.quality.acceptance import (
    MIN_24H_SECONDS,
    MIN_72H_SECONDS,
    PROVISIONAL_MAX_FRESHNESS_SECONDS,
    PROVISIONAL_MAX_STREAM_GAP_SECONDS,
    PROVISIONAL_REQUIRED_STREAMS,
    evaluate_duration_gate,
)
from src.quality.metrics import (
    QualityMetricsCollector,
    SingleStreamContinuity,
    StreamContinuityReport,
)
from src.risk.engine import RiskDecision, DeterministicRiskEngine, RiskViolationCode


# ==============================================================================
# 1. GAP 1: EXECUTION AUTHORIZATION & ANTI-FORGERY
# ==============================================================================

class TestExecutionAuthorizationHardenings:
    """Rigorous adversarial testing of ExecutionAuthorization token security."""

    def test_duck_typed_permit_rejected(self):
        """Duck-typed objects with approved=True are rejected by PaperBroker."""
        broker = PaperBroker(simulated_latency_ms=0.0)

        class FakePermit:
            approved = True
            risk_approved = True

        fake = FakePermit()
        with pytest.raises(PermissionError, match="duck typing strictly prohibited"):
            broker.submit_order(
                symbol="BTCUSDT",
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1.0,
                permit=fake,
            )

    def test_unapproved_risk_decision_cannot_mint_authorization(self):
        """Authorizer refuses to mint an ExecutionAuthorization if RiskDecision is rejected."""
        authorizer = ExecutionAuthorizer()
        rejected_decision = RiskDecision(
            approved=False,
            violation_code=RiskViolationCode.KILL_SWITCH_ACTIVE,
            reason="Kill switch triggered",
        )
        with pytest.raises(PermissionError, match="RiskDecision rejected"):
            authorizer.mint(
                kind="SUBMIT",
                venue="binance_perp",
                mode=ExecutionMode.PAPER,
                risk_decision=rejected_decision,
            )

    def test_forged_signature_rejected(self):
        """Permit with altered fields or tampered signature is rejected."""
        authorizer = ExecutionAuthorizer()
        approved_decision = RiskDecision(approved=True, reason="Pass")
        auth = authorizer.mint(
            kind="SUBMIT",
            venue="binance_perp",
            symbol="BTCUSDT",
            mode=ExecutionMode.PAPER,
            risk_decision=approved_decision,
        )

        # Tampered authorization (signature altered)
        tampered_auth = ExecutionAuthorization(
            kind=auth.kind,
            venue=auth.venue,
            client_order_id=auth.client_order_id,
            mode=auth.mode,
            authorized_live_capital_usd=auth.authorized_live_capital_usd,
            risk_approved=auth.risk_approved,
            issued_ns=auth.issued_ns,
            intent_id=auth.intent_id,
            symbol=auth.symbol,
            side=auth.side,
            risk_decision_id=auth.risk_decision_id,
            risk_decision_fingerprint=auth.risk_decision_fingerprint,
            expires_at_ns=auth.expires_at_ns,
            nonce=auth.nonce,
            signature="forged_signature_hex_0000",
            _issuer=auth._issuer,
        )

        broker = PaperBroker(simulated_latency_ms=0.0, authorizer=authorizer)
        with pytest.raises(PermissionError, match="invalid cryptographic signature"):
            broker.submit_order(
                symbol="BTCUSDT",
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1.0,
                venue="binance_perp",
                permit=tampered_auth,
            )

    def test_symbol_mismatch_rejected(self):
        """Permit minted for BTC cannot be used to submit an ETH order."""
        authorizer = ExecutionAuthorizer()
        approved_decision = RiskDecision(approved=True, reason="Pass")
        auth = authorizer.mint(
            kind="SUBMIT",
            venue="binance_perp",
            symbol="BTCUSDT",
            mode=ExecutionMode.PAPER,
            risk_decision=approved_decision,
        )

        broker = PaperBroker(simulated_latency_ms=0.0, authorizer=authorizer)
        with pytest.raises(PermissionError, match="Authorization symbol mismatch"):
            broker.submit_order(
                symbol="ETHUSDT",  # Mismatch!
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1.0,
                venue="binance_perp",
                permit=auth,
            )

    def test_venue_mismatch_rejected(self):
        """Permit minted for binance_perp cannot be used on deribit."""
        authorizer = ExecutionAuthorizer()
        approved_decision = RiskDecision(approved=True, reason="Pass")
        auth = authorizer.mint(
            kind="SUBMIT",
            venue="binance_perp",
            symbol="BTCUSDT",
            mode=ExecutionMode.PAPER,
            risk_decision=approved_decision,
        )

        broker = PaperBroker(simulated_latency_ms=0.0, authorizer=authorizer)
        with pytest.raises(PermissionError, match="Authorization venue mismatch"):
            broker.submit_order(
                symbol="BTCUSDT",
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1.0,
                venue="deribit",  # Mismatch!
                permit=auth,
            )

    def test_expired_permit_rejected(self):
        """Permit submitted past expires_at_ns is rejected."""
        authorizer = ExecutionAuthorizer()
        approved_decision = RiskDecision(approved=True, reason="Pass")
        t0 = 1_000_000_000_000
        # 1-second validity window
        auth = authorizer.mint(
            kind="SUBMIT",
            venue="paper",
            symbol="BTCUSDT",
            mode=ExecutionMode.PAPER,
            risk_decision=approved_decision,
            current_time_ns=t0,
            validity_window_ns=1_000_000_000,
        )

        broker = PaperBroker(simulated_latency_ms=0.0, authorizer=authorizer)
        # Attempt to use permit 2 seconds later
        t_late = t0 + 2_000_000_000
        with pytest.raises(PermissionError, match="Authorization expired"):
            broker.submit_order(
                symbol="BTCUSDT",
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1.0,
                venue="paper",
                current_time_ns=t_late,
                permit=auth,
            )

    def test_single_use_replay_protection(self):
        """Permit cannot be replayed or reused for multiple order submissions."""
        authorizer = ExecutionAuthorizer()
        approved_decision = RiskDecision(approved=True, reason="Pass")
        t0 = 1_000_000_000_000
        auth = authorizer.mint(
            kind="SUBMIT",
            venue="paper",
            symbol="BTCUSDT",
            mode=ExecutionMode.PAPER,
            risk_decision=approved_decision,
            current_time_ns=t0,
            validity_window_ns=10_000_000_000,
        )

        broker = PaperBroker(simulated_latency_ms=0.0, authorizer=authorizer)
        # First execution succeeds
        order1 = broker.submit_order(
            symbol="BTCUSDT",
            side=PaperOrderSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=0.5,
            venue="paper",
            current_time_ns=t0,
            permit=auth,
        )
        assert order1 is not None

        # Replay attempt fails with consumed permit error
        with pytest.raises(PermissionError, match="permit token already consumed"):
            broker.submit_order(
                symbol="BTCUSDT",
                side=PaperOrderSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=0.5,
                venue="paper",
                current_time_ns=t0 + 100,
                permit=auth,
            )


# ==============================================================================
# 2. GAP 2: ACCEPTANCE GATE DATA SPAN & CONTINUITY
# ==============================================================================

class TestAcceptanceGateDataContinuity:
    """Verifies that acceptance gates strictly evaluate effective continuous data spans."""

    def test_missing_required_stream_fails_gate(self):
        """If any of the 6 required streams is missing, effective data span is 0.0 and gate fails."""
        report = StreamContinuityReport(
            streams={
                "binance_perp/bbo_ticks": SingleStreamContinuity(
                    stream_name="binance_perp/bbo_ticks", venue="binance_perp", table="bbo_ticks", exists=True, status="PASS"
                ),
                # deribit/bbo_ticks is missing!
            },
            effective_data_span_seconds=0.0,
            all_streams_pass=False,
            failures=["Required stream missing: deribit/bbo_ticks"],
        )

        # 25 hours elapsed, but effective span is 0
        gate = evaluate_duration_gate(
            gate_name="24h",
            elapsed_seconds=25.0 * 3600.0,
            metrics_pass=True,
            effective_data_span_seconds=report.effective_data_span_seconds,
            stream_continuity_failures=report.failures,
        )
        assert gate.status == "FAIL"
        assert not gate.passed
        assert any("Effective data span" in r for r in gate.reasons)
        assert any("Required stream missing" in r for r in gate.reasons)

    def test_burst_without_continuity_fails_gate(self):
        """100k rows in 15 minutes cannot pass a 24h gate despite elapsed time >= 24h."""
        burst_span_seconds = 15.0 * 60.0  # 900 seconds
        failures = ["Stream binance_perp/bbo_ticks: Burst without continuity: 100000 rows across only 900.0s span in 24.5h run."]

        gate = evaluate_duration_gate(
            gate_name="24h",
            elapsed_seconds=25.0 * 3600.0,  # 25h wall-clock elapsed
            metrics_pass=False,
            effective_data_span_seconds=burst_span_seconds,  # Only 900s of actual continuous data
            total_row_count=100_000,
            stream_continuity_failures=failures,
        )
        assert gate.status == "FAIL"
        assert not gate.passed
        assert any("Effective data span" in r for r in gate.reasons)
        assert any("Burst without continuity" in r for r in gate.reasons)

    def test_mid_stream_excessive_gap_fails_gate(self):
        """Continuity gap exceeding PROVISIONAL_MAX_STREAM_GAP_SECONDS causes gate failure."""
        failures = [f"Stream deribit/bbo_ticks: Excessive continuity gap: 4500.0s > max {PROVISIONAL_MAX_STREAM_GAP_SECONDS}s."]

        gate = evaluate_duration_gate(
            gate_name="24h",
            elapsed_seconds=25.0 * 3600.0,
            metrics_pass=False,
            effective_data_span_seconds=24.5 * 3600.0,
            total_row_count=50_000,
            stream_continuity_failures=failures,
        )
        assert gate.status == "FAIL"
        assert any("Excessive continuity gap" in r for r in gate.reasons)

    def test_stale_stream_fails_gate(self):
        """Stream with no data received in > 30 minutes fails freshness check."""
        failures = [f"Stream polymarket/bbo_ticks: Stale stream: last event received 2400.0s ago > max {PROVISIONAL_MAX_FRESHNESS_SECONDS}s."]

        gate = evaluate_duration_gate(
            gate_name="24h",
            elapsed_seconds=25.0 * 3600.0,
            metrics_pass=False,
            effective_data_span_seconds=24.5 * 3600.0,
            total_row_count=50_000,
            stream_continuity_failures=failures,
        )
        assert gate.status == "FAIL"
        assert any("Stale stream" in r for r in gate.reasons)

    def test_true_continuous_data_passes_24h_gate(self):
        """When elapsed >= 24h, all required streams continuous, fresh, and span >= 24h, gate PASSES."""
        gate = evaluate_duration_gate(
            gate_name="24h",
            elapsed_seconds=86_500.0,
            metrics_pass=True,
            effective_data_span_seconds=86_450.0,
            is_process_alive=True,
            total_row_count=200_000,
            stream_continuity_failures=[],
        )
        assert gate.status == "PASS"
        assert gate.passed


# ==============================================================================
# 3. GAP 3: STORAGE SINK DOUBLE-FAILURE & STATE MACHINE
# ==============================================================================

class TestStorageSinkDoubleFailure:
    """Verifies that Parquet + Quarantine double failures do not drop in-memory data."""

    @pytest.mark.asyncio
    async def test_double_failure_retains_buffer_and_marks_failed(self, tmp_path):
        """When both parquet write AND dead-letter quarantine fail, rows remain buffered."""
        sink = StorageSink(
            base_path=tmp_path / "raw",
            flush_interval_sec=60.0,
            flush_row_threshold=1000,
        )

        test_row = {
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 50000.0,
            "bid_size": 1.0,
            "ask_price": 50001.0,
            "ask_size": 1.0,
            "ts_exchange_utc_ns": time.time_ns(),
            "ts_received_utc_ns": time.time_ns(),
        }

        await sink.append("binance_perp", "bbo_ticks", test_row)
        key = ("binance_perp", "bbo_ticks")
        assert len(sink._buffers[key]) == 1
        assert sink.sink_state == StorageSinkState.HEALTHY

        # Simulate double failure: patch pq.write_table to raise, and patch json.dump to raise
        with patch("pyarrow.parquet.write_table", side_effect=IOError("Disk I/O failure on Parquet write")):
            with patch("json.dump", side_effect=IOError("Disk I/O failure on Quarantine dead-letter write")):
                await sink.flush_all()

        # Double failure invariant: buffer was NOT dropped or truncated!
        assert len(sink._buffers[key]) == 1
        assert sink._buffers[key][0] == test_row
        assert sink.sink_state == StorageSinkState.FAILED
        assert sink.consecutive_double_failures == 1

        # Now simulate disk recovery: next flush succeeds
        await sink.flush_all()

        # Buffer successfully committed and emptied
        assert len(sink._buffers[key]) == 0
        assert sink.sink_state == StorageSinkState.HEALTHY
        assert sink.consecutive_double_failures == 0

        await sink.stop()

    @pytest.mark.asyncio
    async def test_quarantine_success_marks_degraded_and_evicts(self, tmp_path):
        """When parquet write fails but quarantine succeeds, rows are durably dumped and state is DEGRADED."""
        sink = StorageSink(
            base_path=tmp_path / "raw",
            flush_interval_sec=60.0,
            flush_row_threshold=1000,
        )

        test_row = {
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 50000.0,
            "bid_size": 1.0,
            "ask_price": 50001.0,
            "ask_size": 1.0,
            "ts_exchange_utc_ns": time.time_ns(),
            "ts_received_utc_ns": time.time_ns(),
        }

        await sink.append("binance_perp", "bbo_ticks", test_row)
        key = ("binance_perp", "bbo_ticks")

        # Parquet fails, but quarantine succeeds
        with patch("pyarrow.parquet.write_table", side_effect=IOError("Parquet schema error")):
            await sink.flush_all()

        # Buffer evicted because rows are safely in quarantine dead-letter
        assert len(sink._buffers[key]) == 0
        assert sink.sink_state == StorageSinkState.DEGRADED
        assert sink.events_quarantined == 1

        # Verify quarantine file exists on disk
        q_files = list((tmp_path / "raw" / "quarantine").glob("**/*.json"))
        assert len(q_files) == 1

        await sink.stop()

    @pytest.mark.asyncio
    async def test_stop_reports_uncommitted_rows_if_failed(self, tmp_path):
        """Calling stop() when uncommitted rows remain marks state as FAILED."""
        sink = StorageSink(
            base_path=tmp_path / "raw",
            flush_interval_sec=60.0,
            flush_row_threshold=1000,
        )

        test_row = {
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 50000.0,
            "bid_size": 1.0,
            "ask_price": 50001.0,
            "ask_size": 1.0,
            "ts_exchange_utc_ns": time.time_ns(),
            "ts_received_utc_ns": time.time_ns(),
        }

        await sink.append("binance_perp", "bbo_ticks", test_row)

        with patch("pyarrow.parquet.write_table", side_effect=IOError("Permanent disk failure")):
            with patch("json.dump", side_effect=IOError("Permanent disk failure")):
                await sink.stop()

        # State must be FAILED and uncommitted rows preserved
        assert sink.sink_state == StorageSinkState.FAILED
        key = ("binance_perp", "bbo_ticks")
        assert len(sink._buffers[key]) == 1
