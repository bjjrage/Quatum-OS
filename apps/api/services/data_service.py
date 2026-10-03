"""Data Service for Quant Cockpit API.

Connects FastAPI directly to real Python modules and data artifacts in Trading / Quant OS:
- data/runtime/current_run.json
- data/quality/acceptance_*.json
- src.strategies.registry (create_extended_registry)
- src.strategies.str002_v2 (model variants, BTC decision matrix)
- src.research.experiments (ExperimentRegistry)
- src.research.holdout (SealedHoldoutManager)
- src.portfolio.gates (LatencySensitivityGate, TemporalStabilityGate, etc.)
- src.portfolio.allocator (PortfolioAllocator)
- src.risk.engine (DeterministicRiskEngine)
- src.risk.capital_pockets (CapitalPocket, PropRuleProfile, PropExamMonteCarloSimulator)
- src.paper.broker (PaperBroker)
- src.execution.reconciliation (OrderLifecycleTracker)
- src.attribution.engine (PerformanceAttributionEngine)
"""

from __future__ import annotations

import datetime
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

from src.common.operational_truth import OperationalStatus, is_fresh, safe_metric
from src.persistence.backend import LocalPersistenceBackend
from src.execution_plane.store import ExecutionKillSwitch
from src.execution_plane.service import ExecutionPlaneService

# Domain imports
from src.strategies.registry import (
    create_extended_registry,
    StrategyRegistry,
)
from src.strategies.models import StrategySpec, StrategyStage
from src.strategies.str002_v2 import (
    get_str002_model_variants,
    BtcState,
    BtcStateClassifier,
)
from src.quality.tradability import (
    TradabilityTier,
    TradabilityScore,
    LiquidityTierPolicy,
)
from src.quality.acceptance import (
    RuntimeManifest,
    evaluate_duration_gate,
    AcceptanceState,
    AcceptanceContinuityState,
)
from src.research.experiments import (
    ExperimentRegistry,
    ExperimentRecord,
    RegistryIntegrityStatus,
)
from src.research.holdout import (
    SealedHoldoutManager,
    HoldoutAuditRecord,
    HoldoutStatus,
)
from src.portfolio.gates import (
    GateStatus,
    StrategyGateResult,
    LatencySensitivityGate,
    TemporalStabilityGate,
    MultipleSelectionGate,
    CorrelationCapacityGate,
)
from src.portfolio.allocator import (
    PortfolioAllocator,
    AllocationBudget,
)
from src.paper.broker import (
    PaperBroker,
    PaperOrder,
    PaperOrderSide,
    PaperOrderType,
    PaperOrderStatus,
    PaperTrade,
    PaperPosition,
)
from src.execution.reconciliation import (
    OrderLifecycleTracker,
)
from src.execution.models import (
    OrderIntent,
    OrderState,
    compute_idempotency_key,
)
from src.risk.engine import (
    DeterministicRiskEngine,
    RiskLimits,
    RiskViolationCode,
    RiskDecision,
    ProposedOrder,
)
from src.risk.event_cluster import EventCluster
from src.risk.capital_pockets import (
    CapitalPocket,
    PocketType,
    PropRuleProfile,
    PropProfileVerificationStatus,
    MultiAccountEvidenceGate,
    ManualEvidenceObject,
    PropExamMonteCarloSimulator,
    TradeSample,
)
from src.attribution.engine import (
    PerformanceAttributionEngine,
    StrategyAttribution,
)


class QuantOSDataService:
    """Singleton service providing operational read models from real Quant OS modules."""

    _instance: Optional["QuantOSDataService"] = None

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir or Path.cwd())
        self.data_dir = self.root_dir / "data"

        # Truth invariant: no fixtures unless explicitly requested (QUANT_OS_MOCK_MODE=1).
        self.mock_mode: bool = os.environ.get("QUANT_OS_MOCK_MODE", "0") == "1"
        # Authoritative own-capital baseline (HYPOTHETICAL, not live). Live authorization stays $0.
        self.own_capital_baseline_usd: float = 2_000.0
        self.data_source_default: str = "MOCK" if self.mock_mode else "LOCAL_RUNTIME"

        # Initialize core registry
        self.strategy_registry: StrategyRegistry = create_extended_registry()

        # Initialize paper broker with simulated operational latency (20ms)
        self.paper_broker: PaperBroker = PaperBroker(
            initial_cash_usd=100_000.0 if self.mock_mode else self.own_capital_baseline_usd,
            simulated_latency_ms=20.0,
            maker_fee_bps=1.0,
            taker_fee_bps=5.0,
            base_slippage_bps=2.0,
        )

        # Initialize execution tracker
        self.lifecycle_tracker: OrderLifecycleTracker = OrderLifecycleTracker()

        # Initialize deterministic risk engine with LOCKED live capital ($0 live risk)
        self.risk_limits = RiskLimits(
            max_drawdown_limit_pct=0.10,
            drawdown_warning_pct=0.05,
            max_gross_leverage=3.0,
            max_single_position_pct=0.25,
            live_capital_locked=True,
        )
        self.risk_engine: DeterministicRiskEngine = DeterministicRiskEngine(
            initial_equity_usd=100_000.0 if self.mock_mode else self.own_capital_baseline_usd,
            limits=self.risk_limits,
        )

        # Register standard EventClusters
        self.event_clusters: Dict[str, EventCluster] = {
            "CRYPTO_DIRECTIONAL": EventCluster(
                cluster_id="CRYPTO_DIRECTIONAL",
                description="Systemic crypto beta and market-wide directional drawdown",
                max_gross_exposure_usd=150_000.0,
                max_net_exposure_usd=75_000.0,
                stress_loss_limit_usd=30_000.0,
                stress_factor=0.30,
                member_weights={"BTCUSDT": 1.0, "ETHUSDT": 1.1, "SOLUSDT": 1.4, "DOGEUSDT": 1.6},
            ),
            "DERIBIT_SMILE": EventCluster(
                cluster_id="DERIBIT_SMILE",
                description="Cross-strike volatility smile and synthetic skew dislocation",
                max_gross_exposure_usd=100_000.0,
                max_net_exposure_usd=50_000.0,
                stress_loss_limit_usd=20_000.0,
                stress_factor=0.25,
                member_weights={"BTC-16OCT26-70000-P": 1.0, "BTC-16OCT26-80000-C": 1.0},
            ),
            "POLYMKT_POLITICAL": EventCluster(
                cluster_id="POLYMKT_POLITICAL",
                description="Prediction market political and regulatory binary contracts",
                max_gross_exposure_usd=50_000.0,
                max_net_exposure_usd=25_000.0,
                stress_loss_limit_usd=15_000.0,
                stress_factor=0.50,
                member_weights={"0x01dffa7abae7e5d9b7fb44b06d537c5ac932e2ca422ab4b53366672f5e2dc7d6": 1.0},
            ),
        }
        if not self.mock_mode:
            self.event_clusters = {}  # demo cluster limits are sized to a fictional $100k book
        for ec in self.event_clusters.values():
            self.risk_engine.register_event_cluster(ec)

        # Initialize Capital Pockets
        self.capital_pockets: Dict[str, CapitalPocket] = {
            "OWN_MAIN": CapitalPocket(
                pocket_id="OWN_MAIN",
                pocket_type=PocketType.OWN,
                firm_name="Proprietary Capital",
                account_id="OWN-001",
                initial_equity_usd=100_000.0,
                current_equity_usd=100_000.0,
                peak_equity_usd=100_000.0,
                daily_starting_equity_usd=100_000.0,
                daily_loss_limit_pct=0.05,
                trailing_drawdown_limit_pct=0.10,
                is_frozen=False,
            ),
            "PROP_ALPHA_100K": CapitalPocket(
                pocket_id="PROP_ALPHA_100K",
                pocket_type=PocketType.PROP,
                firm_name="AlphaFunding",
                account_id="AF-EVAL-8821",
                initial_equity_usd=100_000.0,
                current_equity_usd=100_000.0,
                peak_equity_usd=100_000.0,
                daily_starting_equity_usd=100_000.0,
                daily_loss_limit_pct=0.05,
                trailing_drawdown_limit_pct=0.10,
                is_frozen=False,
            ),
            "PROP_BETA_50K": CapitalPocket(
                pocket_id="PROP_BETA_50K",
                pocket_type=PocketType.PROP,
                firm_name="BetaTrader",
                account_id="BT-EVAL-4410",
                initial_equity_usd=50_000.0,
                current_equity_usd=50_000.0,
                peak_equity_usd=50_000.0,
                daily_starting_equity_usd=50_000.0,
                daily_loss_limit_pct=0.04,
                trailing_drawdown_limit_pct=0.08,
                is_frozen=False,
            ),
        }

        if not self.mock_mode:
            own = self.capital_pockets["OWN_MAIN"]
            b = self.own_capital_baseline_usd
            own.initial_equity_usd = own.current_equity_usd = own.peak_equity_usd = own.daily_starting_equity_usd = b
            self.capital_pockets = {"OWN_MAIN": own}

        # Multi-Account Evidence Gate
        self.multi_account_gate = MultiAccountEvidenceGate()
        if self.mock_mode:
            self.multi_account_gate.register_account("AlphaFunding", "AF-EVAL-8821")
            self.multi_account_gate.register_account("BetaTrader", "BT-EVAL-4410")

        # Prop Rule Profiles with verified & pending states
        self.prop_profiles: Dict[str, PropRuleProfile] = {
            "AlphaFunding_v1": PropRuleProfile(
                provider_id="AlphaFunding",
                firm_name="AlphaFunding",
                version="v1.0",
                effective_date="2026-01-01",
                evaluation_execution="SIMULATED",
                funded_execution="SIMULATED",
                payout_type="REAL",
                daily_loss_mode="TRAILING_EQUITY",
                daily_loss_limit_pct=0.05,
                trailing_max_drawdown_pct=0.10,
                max_total_loss_pct=0.10,
                profit_target_pct=0.10,
                min_trading_days=5,
                venue="CRYPTO_FUTURES_BROKER",
                api_bot_policy="ALLOWED",
                tick_scalping_policy="ALLOWED",
                minimum_holding_policy="NO_MINIMUM",
                news_trading_policy="ALLOWED",
                weekend_policy="CLOSE_BEFORE_WEEKEND",
                multi_account_policy="MAX_3_ACCOUNTS",
                copy_trading_policy="ALLOWED_OWN_ACCOUNTS",
                hedging_policy="ALLOWED",
                country_eligibility=["US", "GB", "DE", "SG", "PY"],
                verification_status=PropProfileVerificationStatus.VERIFIED,
                verified_at="2026-09-15T12:00:00Z",
                verified_by="COMPLIANCE_HEAD",
                evidence_refs=["AF_TERMS_2026_SEC4", "AF_API_ADDENDUM"],
            ),
            "GammaProp_v1": PropRuleProfile(
                provider_id="GammaProp",
                firm_name="GammaProp",
                version="v1.0",
                effective_date="2026-03-01",
                # Unknown fields stay UNKNOWN and PENDING per OS invariant
                evaluation_execution="UNKNOWN",
                funded_execution="UNKNOWN",
                payout_type="UNKNOWN",
                daily_loss_limit_pct=0.04,
                trailing_max_drawdown_pct=0.08,
                profit_target_pct=0.08,
                api_bot_policy="UNKNOWN",
                tick_scalping_policy="UNKNOWN",
                minimum_holding_policy="UNKNOWN",
                news_trading_policy="UNKNOWN",
                weekend_policy="UNKNOWN",
                multi_account_policy="UNKNOWN",
                copy_trading_policy="UNKNOWN",
                hedging_policy="UNKNOWN",
                country_eligibility=[],
                verification_status=PropProfileVerificationStatus.PENDING,
                verified_at=None,
                verified_by=None,
            ),
        }

        if not self.mock_mode:
            self.prop_profiles = {}  # fictional providers never exist outside explicit mock mode

        # Prop Simulator
        self.prop_simulator = PropExamMonteCarloSimulator()

        # Attribution engine
        self.attribution_engine = PerformanceAttributionEngine(benchmark_symbol="BTCUSDT")

        # Risk decisions log
        self.risk_decisions: List[Dict[str, Any]] = [
            {
                "decision_id": "DEC-INIT-001",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "strategy_id": "STR-002",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.5,
                "price": 84500.0,
                "approved": False,
                "violation_code": RiskViolationCode.CAPITAL_LOCKED.value,
                "reason": "Live capital locked ($0 live risk invariant). Real order routing physically prevented.",
                "metrics": {"authorized_live_capital": 0.0, "requested_notional": 42250.0},
            }
        ]

        # Audit events log
        self.audit_events: List[Dict[str, Any]] = [
            {
                "audit_id": "AUDIT-001",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "category": "SYSTEM_INITIALIZATION",
                "actor": "OPERATOR",
                "summary": "Quant Cockpit API initialized in LOCAL_PAPER_ONLY mode. Live risk locked ($0).",
                "details": {"git_sha": self._get_git_sha(), "pid": os.getpid()},
            },
            {
                "audit_id": "AUDIT-002",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "category": "GOVERNANCE_INVARIANT",
                "actor": "RISK_ENGINE",
                "summary": "Live capital authorization confirmed locked ($0.00).",
                "details": {"live_capital_locked": True, "authorized_live_budget": 0.0},
            },
        ]

        if not self.mock_mode:
            self.risk_decisions = []
            self.audit_events = []

        # Persistent Control Plane & Scoped Kill Switch Authority
        cp_db = Path(os.environ.get("QUANT_OS_CONTROL_PLANE_DB") or (self.data_dir / "control_plane" / "control_plane.db"))
        self.persistence_backend = LocalPersistenceBackend(db_path=cp_db)
        self.execution_kill_switch = ExecutionKillSwitch(self.persistence_backend)

        # Sync persistent global kill switch into deterministic risk engine on startup
        if self.execution_kill_switch._active.get(("GLOBAL", "")):
            self.risk_engine.trigger_kill_switch("Persisted global kill switch is active")

        # Operational Paper Session State (Invariant: PAPER OPERATIONAL = NOT STARTED)
        self.paper_session_active: bool = False

    def activate_kill_switch(self, scope: str, actor: str, reason: str, target: str = "") -> Dict[str, Any]:
        """Activate scoped kill switch with durable persistence and risk engine sync."""
        self.execution_kill_switch.activate(scope, actor, reason, target)
        if scope == "GLOBAL":
            self.risk_engine.trigger_kill_switch(reason)
        self.audit_events.append({
            "audit_id": f"KS-ACT-{time.time_ns()}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "category": "KILL_SWITCH_ACTIVATED",
            "actor": actor,
            "summary": f"Kill switch activated: scope={scope}, target={target}, reason={reason}",
            "details": {"scope": scope, "target": target, "reason": reason},
        })
        return self.get_risk_status()

    def reset_kill_switch(self, scope: str, actor: str, reason: str, target: str = "") -> Dict[str, Any]:
        """Reset scoped kill switch with durable persistence and risk engine sync."""
        self.execution_kill_switch.reset(scope, actor, reason, target)
        if scope == "GLOBAL":
            self.risk_engine.reset_kill_switch()
        self.audit_events.append({
            "audit_id": f"KS-RST-{time.time_ns()}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "category": "KILL_SWITCH_RESET",
            "actor": actor,
            "summary": f"Kill switch reset: scope={scope}, target={target}, reason={reason}",
            "details": {"scope": scope, "target": target, "reason": reason},
        })
        return self.get_risk_status()

    @classmethod
    def get_instance(cls) -> "QuantOSDataService":
        mode = os.environ.get("QUANT_OS_MOCK_MODE", "0") == "1"
        if cls._instance is None or cls._instance.mock_mode != mode:
            cls._instance = cls()
        return cls._instance

    def _prov(self, real_source: str = "LOCAL_RUNTIME") -> Dict[str, Any]:
        """Provenance block. Fixtures are always labelled MOCK."""
        if self.mock_mode:
            return {"data_source": "MOCK", "status": "MOCK", "is_fixture": True}
        return {"data_source": real_source, "is_fixture": False}

    # --------------------------------------------------------------------------
    # Git & System Info
    # --------------------------------------------------------------------------

    def _get_git_sha(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "UNKNOWN"

    def _get_git_branch(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "UNKNOWN"

    def _get_git_log(self, n: int = 5) -> List[Dict[str, str]]:
        commits = []
        try:
            res = subprocess.run(
                ["git", "log", f"-n{n}", "--pretty=format:%H|%s|%an|%cI"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                for line in res.stdout.strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|")
                        commits.append({
                            "sha": parts[0],
                            "message": parts[1],
                            "author": parts[2],
                            "date": parts[3],
                        })
        except Exception:
            pass
        return commits

    def get_system_status(self) -> Dict[str, Any]:
        git_sha = self._get_git_sha()
        branch = self._get_git_branch()
        rec_status = self.get_recorder_status()
        strategies = self.strategy_registry.list_all()

        stage_counts = {stage.value: 0 for stage in StrategyStage}
        for s in strategies:
            stage_counts[s.stage.value] = stage_counts.get(s.stage.value, 0) + 1

        exp_data = self.get_experiments()
        total_exp = exp_data.get("total", 0)

        # Latest quality report
        latest_report = self._load_latest_quality_report()
        gates_info = latest_report.get("gates", {}) if latest_report else {}
        g24 = gates_info.get("gate_24h", {})
        g72 = gates_info.get("gate_72h", {})

        g24_status = g24.get("status", rec_status.get("gate_24h_status", "PENDING"))
        g24_passed = (g24_status == "PASS") and bool(g24.get("passed", False))

        g72_status = g72.get("status", rec_status.get("gate_72h_status", "PENDING"))
        g72_passed = (g72_status == "PASS") and bool(g72.get("passed", False))

        return {
            "status": "OPERATIONAL",
            "environment": "LOCAL_PAPER_ONLY",
            "git_sha": git_sha,
            "git_sha_short": git_sha[:7] if git_sha else "UNKNOWN",
            "branch": branch,
            "live_capital_state": "LOCKED",
            "authorized_live_capital_usd": 0.0,
            "live_trading_locked": True,
            "recorder_status": rec_status.get("status", "UNKNOWN"),
            "recorder_continuity": rec_status.get("continuity_state", "UNVERIFIED"),
            "gate_24h": {
                "status": g24_status,
                "elapsed_seconds": g24.get("elapsed_seconds", rec_status.get("elapsed_seconds", 0.0)),
                "required_seconds": 86400.0,
                "passed": g24_passed,
                "reasons": g24.get("reasons", ["Gate duration requirement not met (< 24h)."]),
            },
            "gate_72h": {
                "status": g72_status,
                "elapsed_seconds": g72.get("elapsed_seconds", rec_status.get("elapsed_seconds", 0.0)),
                "required_seconds": 259200.0,
                "passed": g72_passed,
                "reasons": g72.get("reasons", ["Gate duration requirement not met (< 72h)."]),
            },
            "strategies_total": len(strategies),
            "strategies_by_stage": stage_counts,
            "total_experiments": total_exp,
            "failed_gates": None,  # not computed here: MISSING != ZERO
            "risk_state": "CAPITAL_LOCKED",
            "paper_pnl_usd": (self.paper_broker.cash_usd - self.paper_broker.initial_cash_usd) if (self.paper_session_active or self.mock_mode) else None,
            "system_alerts": [
                {
                    "level": "INFO",
                    "code": "LIVE_CAPITAL_LOCKED",
                    "message": "Live risk locked ($0 Live Capital). Live routing disabled. Paper operational: NOT_STARTED.",
                }
            ],
            "last_heartbeat": rec_status.get("heartbeat_at_utc") or "UNKNOWN",
            "ci_state": "UNKNOWN",
            "mock_mode": self.mock_mode,
            "data_source": "MOCK" if self.mock_mode else "REAL_RUNTIME",
            "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tests_passing": None,
            "tests_failing": None,
        }

    # --------------------------------------------------------------------------
    # Recorder Health & Quality
    # --------------------------------------------------------------------------

    def get_recorder_status(self) -> Dict[str, Any]:
        try:
            manifest_path = self.data_dir / "runtime" / "current_run.json"
            if not manifest_path.exists():
                return {
                    "status": "STOPPED",
                    "continuity_state": "UNVERIFIED",
                    "data_source": "UNAVAILABLE",
                    "heartbeat_at_utc": None,
                    "message": "current_run.json does not exist",
                    "elapsed_seconds": 0.0,
                    "progress_24h_pct": 0.0,
                    "progress_72h_pct": 0.0,
                    "venues": {},
                    "is_process_alive": False,
                }

            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            pid = data.get("pid", 0)
            is_alive = psutil.pid_exists(pid) if pid > 0 else False
            started_ns = data.get("started_at_timestamp_ns", 0)
            now_ns = time.time_ns()
            elapsed_s = max(0.0, (now_ns - started_ns) / 1e9) if started_ns > 0 else 0.0

            # Compute gate progress percentages
            prog_24h = min(100.0, (elapsed_s / 86400.0) * 100.0)
            prog_72h = min(100.0, (elapsed_s / 259200.0) * 100.0)

            # Latest quality report data for venue stats
            latest_report = self._load_latest_quality_report()
            venue_feeds = latest_report.get("venue_feeds", {}) if latest_report else {}
            storage = latest_report.get("storage_metrics", {}) if latest_report else {}
            ts_integrity = latest_report.get("timestamp_integrity", {}) if latest_report else {}
            stream_continuity = latest_report.get("stream_continuity", {}) if latest_report else {}
            gates_info = latest_report.get("gates", {}) if latest_report else {}
            g24_report = gates_info.get("gate_24h", {})
            g72_report = gates_info.get("gate_72h", {})

            # Authoritative gate statuses from quality report, NOT wall-clock ready
            g24_st = g24_report.get("status") or ("PENDING" if is_alive else "UNKNOWN")
            g72_st = g72_report.get("status") or ("PENDING" if is_alive else "UNKNOWN")
            committed_data_span_s = stream_continuity.get("effective_data_span_seconds")

            # Timing and clock integrity (missing measurement is None, NOT 0.0)
            est_offset = ts_integrity.get("estimated_clock_offset_ms") if ts_integrity else None
            has_clock = est_offset is not None
            lag_ms = abs(est_offset) if has_clock else None
            clock_skew_ms = est_offset if has_clock else None
            clock_skew_detected = ts_integrity.get("is_host_clock_skew_detected") if has_clock else None

            # Manifest integrity
            m_valid = storage.get("manifest_valid") if storage else None
            manifest_health = "VALID" if m_valid is True else ("INVALID" if m_valid is False else "UNVERIFIED")

            # Storage sink state
            p_files = storage.get("parquet_file_count", 0) if storage else 0
            if not is_alive:
                sink_state = "STOPPED"
            elif p_files > 0:
                sink_state = "WRITING"
            else:
                sink_state = "IDLE"

            venues_out: Dict[str, Any] = {}
            for v_name in ["polymarket", "deribit", "binance_perp"]:
                v_data = venue_feeds.get(v_name, {})
                last_ts = v_data.get("last_event_received_at_utc")
                fresh = False
                if last_ts:
                    try:
                        dt = datetime.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                        age_s = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds()
                        fresh = (age_s <= 1800.0)
                    except Exception:
                        fresh = False

                if not is_alive:
                    v_connected = False
                    v_feed_health = "PROCESS_DOWN"
                elif last_ts is None:
                    # Missing evidence is UNKNOWN, not connected
                    v_connected = None
                    v_feed_health = "UNKNOWN"
                elif fresh:
                    v_connected = True
                    v_feed_health = "HEALTHY"
                else:
                    v_connected = False
                    v_feed_health = "STALE"

                venues_out[v_name] = {
                    "venue": v_name,
                    "connected": v_connected,
                    "feed_health": v_feed_health,
                    "last_event_timestamp": last_ts,
                    "total_events": v_data.get("total_events"),
                    "event_rate": round(v_data["total_events"] / max(1.0, elapsed_s), 1) if (v_data.get("total_events") is not None and elapsed_s > 0) else None,
                    "lag_ms": lag_ms,
                    "clock_skew_detected": clock_skew_detected,
                    "clock_skew_ms": clock_skew_ms,
                    "files_written": p_files,
                    "manifest_health": manifest_health,
                    "dropped_or_invalid_events": ts_integrity.get("true_causal_violations") if ts_integrity else None,
                    "storage_size_bytes": storage.get("total_compressed_bytes", 0) if storage else 0,
                    "unique_symbols_count": v_data.get("unique_symbols_count"),
                }

            # Add Bybit status (adapter exists, continuous integration pending)
            venues_out["bybit"] = {
                "venue": "bybit",
                "connected": False,
                "feed_health": "INTEGRATION_PENDING",
                "status": "ADAPTER_READY_INTEGRATION_PENDING",
                "last_event_timestamp": None,
                "total_events": 0,
                "event_rate": 0.0,
                "manifest_health": "PENDING",
                "notes": "Bybit linear adapter implemented in src/collectors/bybit_adapter.py. Live socket wiring pending.",
            }

            # Hardening 01 required feeds status breakdown
            req_feeds = [
                "binance_perp/bbo_ticks",
                "binance_perp/trade_ticks",
                "deribit/bbo_ticks",
                "deribit/deribit_metrics",
                "polymarket/orderbook_l2_depth",
                "polymarket/bbo_ticks",
            ]
            stream_metrics = latest_report.get("stream_metrics", {}) if latest_report else {}
            feed_states = {}
            for sf in req_feeds:
                sf_data = stream_metrics.get(sf, {})
                sf_rows = sf_data.get("row_count")
                sf_last = sf_data.get("last_event_timestamp")
                sf_fresh = False
                if sf_last:
                    try:
                        dt = datetime.datetime.fromisoformat(sf_last.replace("Z", "+00:00"))
                        sf_fresh = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() <= 1800.0
                    except Exception:
                        pass
                feed_states[sf] = {
                    "stream": sf,
                    "status": "HEALTHY" if sf_fresh else ("STALE" if sf_last else "UNKNOWN"),
                    "row_count": sf_rows,
                    "last_event_timestamp": sf_last,
                    "fresh": sf_fresh if sf_last else None,
                }

            status_val = "RUNNING" if is_alive else "STOPPED"

            return {
                "run_id": data.get("run_id"),
                "git_sha": data.get("git_sha") or "UNKNOWN",
                "pid": pid,
                "is_process_alive": is_alive,
                "storage_sink_state": sink_state,
                "all_venues_connected": False if not is_alive else None,
                "all_feeds_healthy": False if not is_alive else None,
                "started_at_utc": data.get("started_at_utc"),
                "heartbeat_at_utc": data.get("heartbeat_at_utc"),
                "config_fingerprint": data.get("config_fingerprint"),
                "status": status_val,
                "data_source": "REAL_RUNTIME",
                "continuity_state": data.get("continuity_state", "UNVERIFIED"),
                "continuity_reason": data.get("continuity_reason", "NOT_REPORTED_BY_MANIFEST"),
                "elapsed_seconds": elapsed_s,
                "process_uptime_seconds": elapsed_s,
                "committed_data_span_seconds": committed_data_span_s,
                "elapsed_formatted": self._format_seconds(elapsed_s),
                "progress_24h_pct": round(prog_24h, 2),
                "progress_72h_pct": round(prog_72h, 2),
                "gate_24h_status": g24_st,
                "gate_72h_status": g72_st,
                "venues": venues_out,
                "required_feeds": feed_states,
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "continuity_state": "BROKEN",
                "error": str(e),
                "elapsed_seconds": 0.0,
                "process_uptime_seconds": 0.0,
                "committed_data_span_seconds": None,
                "gate_24h_status": "UNKNOWN",
                "gate_72h_status": "UNKNOWN",
                "venues": {},
                "is_process_alive": False,
            }

    def _format_seconds(self, s: float) -> str:
        hrs = int(s // 3600)
        mins = int((s % 3600) // 60)
        secs = int(s % 60)
        return f"{hrs}h {mins:02d}m {secs:02d}s"

    def _load_latest_quality_report(self) -> Optional[Dict[str, Any]]:
        quality_dir = self.data_dir / "quality"
        if not quality_dir.exists():
            return None
        files = sorted(quality_dir.glob("acceptance_*.json"), key=lambda p: p.stat().st_mtime)
        if not files:
            return None
        latest_file = files[-1]
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_data_quality(self) -> Dict[str, Any]:
        latest = self._load_latest_quality_report()
        if not latest:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "No acceptance quality report files found in data/quality",
            }

        # Scan all acceptance files to provide chronological timeline
        quality_dir = self.data_dir / "quality"
        history = []
        for p in sorted(quality_dir.glob("acceptance_*.json"), key=lambda x: x.stat().st_mtime):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    rep = json.load(f)
                meta = rep.get("report_metadata", {})
                st = rep.get("storage_metrics", {})
                ts = rep.get("timestamp_integrity", {})
                history.append({
                    "filename": p.name,
                    "generated_at_utc": meta.get("generated_at_utc"),
                    "total_events": st.get("total_row_count", 0),
                    "files_count": st.get("parquet_file_count", 0),
                    "orphan_tmp_files": st.get("orphan_tmp_files", 0),
                    "manifest_valid": st.get("manifest_valid", True),
                    "clock_offset_ms": ts.get("estimated_clock_offset_ms", 0.0),
                    "corrected_p50_ms": ts.get("corrected_latency_p50_ms", 0.0),
                    "corrected_p95_ms": ts.get("corrected_latency_p95_ms", 0.0),
                    "corrected_p99_ms": ts.get("corrected_latency_p99_ms", 0.0),
                })
            except Exception:
                continue

        return {
            "status": "AVAILABLE",
            "report_metadata": latest.get("report_metadata", {}),
            "run_metadata": latest.get("run_metadata", {}),
            "runtime_health": latest.get("runtime_health", {}),
            "storage_metrics": latest.get("storage_metrics", {}),
            "timestamp_integrity": latest.get("timestamp_integrity", {}),
            "venue_feeds": latest.get("venue_feeds", {}),
            "coverage_metrics": latest.get("coverage_metrics", {}),
            "gates": latest.get("gates", {}),
            "history": history,
        }

    # --------------------------------------------------------------------------
    # Tradability & Markets
    # --------------------------------------------------------------------------

    def get_markets_tradability(self) -> Dict[str, Any]:
        if not self.mock_mode:
            # No real market-snapshot source is wired: never fabricate spread/depth/volume/OI/vol.
            return {
                "status": "NOT_AVAILABLE",
                "data_source": "UNAVAILABLE",
                "reason": "No real tradability snapshot source configured",
                "markets": [],
            }
        policy = LiquidityTierPolicy(
            max_spread_bps=15.0,
            min_depth_0_5pct_usd=25_000.0,
            min_volume_5m_usd=100_000.0,
            max_clock_skew_ms=500.0,
            require_valid_manifest=True,
            tier5_max_position_usd=5_000.0,
        )

        # Point in time evaluation of monitored universe
        now_ns = time.time_ns()
        market_samples = [
            {
                "symbol": "BTCUSDT",
                "venue": "binance_perp",
                "spread_bps": 0.8,
                "depth_0_5pct_usd": 650_000.0,
                "volume_5m_usd": 4_200_000.0,
                "oi_usd": 450_000_000.0,
                "rv_5m": 0.0018,
                "clock_sync_offset_ms": 12.0,
                "manifest_valid": True,
            },
            {
                "symbol": "ETHUSDT",
                "venue": "binance_perp",
                "spread_bps": 1.2,
                "depth_0_5pct_usd": 380_000.0,
                "volume_5m_usd": 2_100_000.0,
                "oi_usd": 220_000_000.0,
                "rv_5m": 0.0024,
                "clock_sync_offset_ms": 14.0,
                "manifest_valid": True,
            },
            {
                "symbol": "SOLUSDT",
                "venue": "binance_perp",
                "spread_bps": 3.4,
                "depth_0_5pct_usd": 140_000.0,
                "volume_5m_usd": 850_000.0,
                "oi_usd": 85_000_000.0,
                "rv_5m": 0.0042,
                "clock_sync_offset_ms": 15.0,
                "manifest_valid": True,
            },
            {
                "symbol": "DOGEUSDT",
                "venue": "binance_perp",
                "spread_bps": 7.0,
                "depth_0_5pct_usd": 65_000.0,
                "volume_5m_usd": 280_000.0,
                "oi_usd": 32_000_000.0,
                "rv_5m": 0.0065,
                "clock_sync_offset_ms": 12.0,
                "manifest_valid": True,
            },
            {
                "symbol": "MEMEUSDT",
                "venue": "binance_perp",
                "spread_bps": 11.5,
                "depth_0_5pct_usd": 35_000.0,
                "volume_5m_usd": 120_000.0,
                "oi_usd": 8_500_000.0,
                "rv_5m": 0.0095,
                "clock_sync_offset_ms": 15.0,
                "manifest_valid": True,
            },
            {
                # Marginal liquidity: strictly TIER 5 SMALL TRADABLE (tradable with size limit)
                "symbol": "SUIUSDT",
                "venue": "binance_perp",
                "spread_bps": 13.8,
                "depth_0_5pct_usd": 28_000.0,
                "volume_5m_usd": 110_000.0,
                "oi_usd": 4_200_000.0,
                "rv_5m": 0.0120,
                "clock_sync_offset_ms": 10.0,
                "manifest_valid": True,
            },
            {
                # Fails spread ceiling (>15 bps) -> UNTRADABLE
                "symbol": "ILLIQUID_ALT",
                "venue": "binance_perp",
                "spread_bps": 24.5,
                "depth_0_5pct_usd": 12_000.0,
                "volume_5m_usd": 45_000.0,
                "oi_usd": 500_000.0,
                "rv_5m": 0.0180,
                "clock_sync_offset_ms": 15.0,
                "manifest_valid": True,
            },
            {
                # Fails clock sync (>500ms) -> UNTRADABLE
                "symbol": "SKEWED_FEED",
                "venue": "binance_perp",
                "spread_bps": 2.0,
                "depth_0_5pct_usd": 100_000.0,
                "volume_5m_usd": 500_000.0,
                "oi_usd": 12_000_000.0,
                "rv_5m": 0.003,
                "clock_sync_offset_ms": 620.0,
                "manifest_valid": True,
            },
        ]

        scored_markets = []
        tier_names = {
            1: "TIER 1 (LARGE CAP)",
            2: "TIER 2 (MID CAP)",
            3: "TIER 3 (SMALL CAP)",
            4: "TIER 4 (MICRO CAP)",
            5: "TIER 5 SMALL TRADABLE",
            6: "UNTRADABLE",
        }

        for item in market_samples:
            score: TradabilityScore = policy.evaluate(
                symbol=item["symbol"],
                timestamp_ns=now_ns,
                spread_bps=item["spread_bps"],
                depth_0_5pct_usd=item["depth_0_5pct_usd"],
                volume_5m_usd=item["volume_5m_usd"],
                clock_sync_offset_ms=item["clock_sync_offset_ms"],
                manifest_valid=item["manifest_valid"],
            )

            scored_markets.append({
                "symbol": item["symbol"],
                "venue": item["venue"],
                "tier_code": score.tier.value,
                "tier_name": tier_names.get(score.tier.value, "UNKNOWN"),
                "tradable": score.tradable,
                "spread_bps": score.spread_bps,
                "depth_0_5pct_usd": score.depth_0_5pct_usd,
                "volume_5m_usd": score.volume_5m_usd,
                "oi_usd": item.get("oi_usd"),
                "rv_5m": item.get("rv_5m"),
                "clock_sync_offset_ms": score.clock_sync_offset_ms,
                "manifest_valid": score.manifest_valid,
                "max_position_usd": score.max_position_usd,
                "limit_orders_only": score.limit_orders_only,
                "rejection_reasons": score.rejection_reasons,
                "evaluated_at_ns": score.timestamp_ns,
            })

        return {
            "status": "MOCK",
            "data_source": "MOCK",
            "is_fixture": True,
            "policy": {
                "max_spread_bps": policy.max_spread_bps,
                "min_depth_0_5pct_usd": policy.min_depth_0_5pct_usd,
                "min_volume_5m_usd": policy.min_volume_5m_usd,
                "max_clock_skew_ms": policy.max_clock_skew_ms,
                "tier5_max_position_usd": policy.tier5_max_position_usd,
            },
            "markets": scored_markets,
        }

    # --------------------------------------------------------------------------
    # Strategies & Seed Programs
    # --------------------------------------------------------------------------

    def get_strategies(self) -> List[Dict[str, Any]]:
        out = []
        for s in self.strategy_registry.list_all():
            ct = s.counterparty_thesis
            out.append({
                "strategy_id": s.strategy_id,
                "name": s.name,
                "family": s.family,
                "origin": s.origin.value,
                "stage": s.stage.value,
                "description": s.description,
                "version": s.metadata.get("version", "1.0.0"),
                "display_name": s.metadata.get("display_name", s.name),
                "is_privileged": s.is_privileged,
                "math_foundation_validated": s.math_foundation_validated,
                "economic_edge_validated": s.economic_edge_validated,
                "economic_edge_status": "VALIDATED" if s.economic_edge_validated else "NOT VALIDATED",
                "trial_count": s.trial_count,
                "counterparty_thesis_status": ct.evidence_status.value if ct else "NONE",
                "rules_count": len(s.rules_evidence),
                "paper_eligibility": s.stage in (StrategyStage.VALIDATION, StrategyStage.HOLDOUT, StrategyStage.PAPER),
                "live_eligibility": False,  # Live capital strictly locked
                "execution_mode": s.metadata.get("execution_mode", "UNRESTRICTED"),
            })
        return out

    def get_strategy_detail(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        try:
            s = self.strategy_registry.get(strategy_id)
        except Exception:
            return None

        ct = s.counterparty_thesis
        thesis_data = None
        if ct:
            thesis_data = {
                "counterparty_type": ct.counterparty_type,
                "economic_mechanism": ct.economic_mechanism,
                "why_trade_now": ct.why_trade_now,
                "why_impact_may_be_transient": ct.why_impact_may_be_transient,
                "why_it_may_be_information": ct.why_it_may_be_information,
                "observable_evidence": ct.observable_evidence,
                "falsification_conditions": ct.falsification_conditions,
                "evidence_status": ct.evidence_status.value,
                "is_complete_for_validation": ct.is_complete_for_validation(),
            }

        rules_data = []
        for r in s.rules_evidence:
            rules_data.append({
                "rule_id": r.rule_id,
                "strategy_id": r.strategy_id,
                "description": r.description,
                "status": r.status.value,
                "experiment_ids": r.experiment_ids,
                "strategy_version": r.strategy_version,
                "first_proposed_at": r.first_proposed_at,
                "last_validated_at": r.last_validated_at,
                "notes": r.notes,
            })

        return {
            "strategy_id": s.strategy_id,
            "name": s.name,
            "family": s.family,
            "origin": s.origin.value,
            "stage": s.stage.value,
            "description": s.description,
            "metadata": s.metadata,
            "is_privileged": s.is_privileged,
            "trial_count": s.trial_count,
            "math_foundation_validated": s.math_foundation_validated,
            "economic_edge_validated": s.economic_edge_validated,
            "economic_edge_status": "VALIDATED" if s.economic_edge_validated else "NOT VALIDATED",
            "counterparty_thesis": thesis_data,
            "rules_evidence": rules_data,
            "parameters": s.parameters.parameters if s.parameters else {},
        }

    def get_str002_specialized(self) -> Dict[str, Any]:
        """Specialized quantitative view for STR-002 v2 Liquidity Shock Reversal."""
        try:
            strat = self.strategy_registry.get("STR-002")
        except Exception:
            return {"status": "NOT_AVAILABLE", "reason": "STR-002 not in registry"}

        variants = get_str002_model_variants()

        # BTC State Decision Matrix Specification
        btc_matrix = [
            {
                "state": BtcState.FLAT.value,
                "horizon_1m": "|ret| < 1.0 sigma",
                "horizon_5m": "|ret| < 1.0 sigma",
                "decision": "ALLOWED_AFTER_REVERSAL",
                "sizing": "100%",
                "action": "Proceed with candidate trade targeting pre-shock equilibrium reference price",
            },
            {
                "state": BtcState.UP.value,
                "horizon_1m": "ret >= 1.0 sigma",
                "horizon_5m": "ret >= 1.0 sigma",
                "decision": "ALLOWED_EXTENDED_RUNNER",
                "sizing": "100% (capped; no above-100% sizing permitted)",
                "action": "Proceed with candidate trade, allow trail runner when systemic market is supportive",
            },
            {
                "state": BtcState.DOWN.value,
                "horizon_1m": "ret <= -1.0 sigma",
                "horizon_5m": "ret <= -1.0 sigma",
                "decision": "NEW_ENTRY_BLOCKED",
                "sizing": "0%",
                "action": "Block all new entries; force early exit if currently holding position",
            },
            {
                "state": BtcState.RUNNING_HARD_DOWN.value,
                "horizon_1m": "ret <= -3.0 sigma",
                "horizon_5m": "ret <= -3.0 sigma (or -2.0 sigma with volume expansion > 2.0x)",
                "decision": "STRICTLY_BLOCKED",
                "sizing": "0%",
                "action": "Systemic liquidation cascade active; knife-catching strictly forbidden",
            },
            {
                "state": BtcState.RUNNING_HARD_UP.value,
                "horizon_1m": "ret >= 3.0 sigma",
                "horizon_5m": "ret >= 3.0 sigma (or +2.0 sigma with volume expansion > 2.0x)",
                "decision": "BLOCKED",
                "sizing": "0%",
                "action": "High dispersion / market dislocation; abstain from impulse entries",
            },
        ]

        # Real observed/derived values or NO DATA
        real_metrics = {
            "beta_down": None,
            "beta_up": None,
            "gamma_eth": None,
            "residual_z_score": None,
            "reversal_detector": None,
            "pre_shock_vwap": None,
            "reference_price": None,
            "mfe_usd": None,
            "mae_usd": None,
            "time_to_retracement_s": None,
            "status": "NO LIVE DATA",
            "message": "STR-002 is in RESEARCH stage. Model parameters and residual state require active live candle feed.",
        }

        return {
            "strategy_id": "STR-002",
            "version": "2.0.0",
            "display_name": "STR-002 v2 — Liquidity Shock Reversal",
            "execution_mode": "LONG_ONLY",
            "short_side": "RESEARCH_ONLY ($0 live risk, 0 orders)",
            "economic_edge_status": "NOT VALIDATED",
            "math_foundation_status": "EMPIRICAL_PROTOTYPE",
            "model_variants": variants,
            "btc_decision_matrix": btc_matrix,
            "live_factor_state": real_metrics,
        }

    # --------------------------------------------------------------------------
    # Research & Experiments
    # --------------------------------------------------------------------------

    def get_experiments(self) -> Dict[str, Any]:
        exp_dir = self.data_dir / "experiments"
        try:
            reg = ExperimentRegistry(storage_dir=exp_dir)
            experiments = reg.list_all()
            return {
                "status": "HEALTHY",
                "total": len(experiments),
                "strategy_trial_counts": reg._strategy_trial_counts,
                "quarantine_log": reg.quarantine_log,
                "experiments": [e.model_dump() for e in experiments],
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "reason": str(e),
                "total": 0,
                "experiments": [],
            }

    def get_experiment_detail(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        exp_dir = self.data_dir / "experiments"
        try:
            reg = ExperimentRegistry(storage_dir=exp_dir)
            record = reg.get_experiment(experiment_id)
            return record.model_dump() if record else None
        except Exception:
            return None

    # --------------------------------------------------------------------------
    # Holdout
    # --------------------------------------------------------------------------

    def get_holdouts(self) -> Dict[str, Any]:
        audit_path = self.data_dir / "research" / "holdout_audits.json"
        try:
            manager = SealedHoldoutManager(audit_storage_path=audit_path, raise_on_corruption=False)
            audits = manager._audits
            status = manager.get_status()
            warning_msg = (
                "HOLDOUT GOVERNANCE LOCKED: Storage integrity issue detected."
                if status == "GOVERNANCE_LOCKED"
                else "Holdout governance active. Opening a preregistered dataset permanently burns it for this strategy lineage."
            )
            return {
                "status": status,
                "governance_status": status,
                "warning": warning_msg,
                "total_openings": len(audits),
                "audits": [a.model_dump() for a in audits],
            }
        except Exception as e:
            return {
                "status": "GOVERNANCE_LOCKED",
                "governance_status": "GOVERNANCE_LOCKED",
                "warning": "HOLDOUT GOVERNANCE LOCKED: Storage integrity issue detected.",
                "reason": str(e),
                "total_openings": 0,
                "audits": [],
            }

    # --------------------------------------------------------------------------
    # Portfolio Selection Gates
    # --------------------------------------------------------------------------

    def get_gates_summary(self) -> Dict[str, Any]:
        """Provides the specification, provisional thresholds, and current status for all 4 gates."""
        gate_defs = [
            {
                "gate_id": "A",
                "gate_name": "Gate A: Latency Sensitivity",
                "gate_type": "LATENCY_SENSITIVITY",
                "thresholds": {
                    "max_sharpe_drop_pct_at_5s": 0.50,
                    "min_edge_half_life_s": 5.0,
                    "latency_safety_margin_multiplier": 2.0,
                },
                "threshold_is_provisional": True,
                "evaluation_status": "PENDING",
                "description": "Replays backtest across simulated execution latencies (+1s, +5s, +30s). Rejects LATENCY_RACE strategies.",
                "metrics_evaluated": ["p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "edge_half_life_s", "break_even_latency_s", "latency_safety_margin"],
            },
            {
                "gate_id": "B",
                "gate_name": "Gate B: Temporal Stability & Alpha Decay",
                "gate_type": "TEMPORAL_STABILITY",
                "thresholds": {
                    "min_decay_ratio": 0.50,
                    "min_positive_rolling_pct": 0.75,
                },
                "threshold_is_provisional": True,
                "evaluation_status": "PENDING",
                "description": "Validates that returns do not concentrate in early training periods. Checks rolling 30-day positive consistency.",
                "metrics_evaluated": ["first_half_sharpe", "second_half_sharpe", "decay_ratio", "pct_positive_rolling"],
            },
            {
                "gate_id": "C",
                "gate_name": "Gate C: Multiple Selection Correction",
                "gate_type": "MULTIPLE_SELECTION",
                "thresholds": {
                    "min_dsr": 0.50,
                    "max_adjusted_pvalue": 0.05,
                },
                "threshold_is_provisional": True,
                "evaluation_status": "PENDING",
                "description": "Bailey & López de Prado Deflated Sharpe Ratio (DSR) and Benjamini-Hochberg False Discovery Rate (FDR).",
                "metrics_evaluated": ["dsr", "expected_max_null_sharpe", "adjusted_p_value", "trial_count"],
            },
            {
                "gate_id": "D",
                "gate_name": "Gate D: Correlation & Capacity",
                "gate_type": "CORRELATION_CAPACITY",
                "thresholds": {
                    "max_normal_correlation": 0.60,
                    "max_stress_correlation": 0.70,
                    "max_capacity_volume_pct": 0.01,
                },
                "threshold_is_provisional": True,
                "evaluation_status": "PENDING",
                "description": "Cross-strategy correlation under normal and stressed regimes, EventCluster overlap, and 1% 5m volume capacity.",
                "metrics_evaluated": ["max_normal_correlation", "max_stress_correlation", "proposed_allocation_usd", "capacity_ceiling_usd"],
            },
        ]

        return {
            "status": "AVAILABLE",
            "provenance_invariant": "Green PASS is strictly forbidden if dataset or config provenance is missing or falsified.",
            "gates": gate_defs,
        }

    # --------------------------------------------------------------------------
    # Portfolio Allocation & Regimes
    # --------------------------------------------------------------------------

    def get_portfolio_state(self) -> Dict[str, Any]:
        allocator = PortfolioAllocator(
            total_equity_usd=100_000.0 if self.mock_mode else self.own_capital_baseline_usd,
            max_strategy_allocation_pct=0.40,
            small_live_absolute_cap_usd=5_000.0,
            small_live_max_pct=0.05,
            max_cluster_allocation_pct=0.30,
            live_capital_locked=True,
        )

        strategies = self.strategy_registry.list_all()
        budgets = allocator.allocate(strategies)

        allocations = []
        for s_id, b in budgets.items():
            allocations.append({
                "strategy_id": b.strategy_id,
                "stage": b.stage.value,
                "base_budget_usd": b.base_budget_usd,
                "allocated_capital_usd": b.allocated_capital_usd,
                "allocation_pct": b.allocation_pct,
                "is_live_eligible": b.is_live_eligible,
                "authorized_live_budget": b.authorized_live_budget,
                "paper_budget_usd": b.paper_budget_usd,
                "action": b.action.value,
                "capacity_cap_usd": b.capacity_cap_usd,
                "notes": b.notes,
            })

        return {
            **({"data_source": "MOCK", "status": "MOCK", "is_fixture": True} if self.mock_mode
               else {"data_source": "DERIVED", "status": "CONFIG_BASELINE", "equity_state_kind": "HYPOTHETICAL"}),
            "total_portfolio_equity_usd": 100_000.0 if self.mock_mode else self.own_capital_baseline_usd,
            "live_capital_state": "LOCKED",
            "authorized_live_capital_usd": 0.0,
            "allocations": allocations,
            "event_cluster_exposures": {
                cid: {"gross_usd": 0.0, "net_usd": 0.0, "cap_usd": ec.max_gross_exposure_usd, "utilization_pct": 0.0}
                for cid, ec in self.event_clusters.items()
            },
        }

    # --------------------------------------------------------------------------
    # Paper Trading & Broker
    # --------------------------------------------------------------------------

    def get_paper_account(self) -> Dict[str, Any]:
        if not (self.paper_session_active or self.mock_mode):
            return {
                "data_source": "PAPER_SIMULATION",
                "status": "NOT_STARTED",
                "operational_state": "NOT_STARTED",
                "is_fixture": False,
                "state_kind": "PAPER",
                "is_own_capital": False,
                "persisted": False,
                "initial_cash_usd": None,
                "cash_usd": None,
                "equity_usd": None,
                "realized_pnl_usd": None,
                "unrealized_pnl_usd": None,
                "simulated_latency_ms": self.paper_broker.simulated_latency_ms,
                "maker_fee_bps": self.paper_broker.maker_fee_bps,
                "taker_fee_bps": self.paper_broker.taker_fee_bps,
                "base_slippage_bps": self.paper_broker.base_slippage_bps,
                "positions": [],
                "orders": [],
                "fills": [],
                "message": "Paper broker session is NOT_STARTED. Live risk locked at $0.",
            }

        positions_out = []
        for sym, pos in self.paper_broker.positions.items():
            positions_out.append({
                "symbol": sym,
                "quantity": pos.quantity,
                "average_entry_price": pos.average_entry_price,
                "realized_pnl_usd": pos.realized_pnl_usd,
            })

        orders_out = []
        for o in self.paper_broker.orders.values():
            orders_out.append({
                "order_id": o.order_id,
                "symbol": o.symbol,
                "venue": o.venue,
                "side": o.side.value,
                "order_type": o.order_type.value,
                "quantity": o.quantity,
                "limit_price": o.limit_price,
                "status": o.status.value,
                "submitted_at_ns": o.submitted_at_ns,
                "filled_qty": o.filled_qty,
                "filled_price": o.filled_price,
                "fee_paid": o.fee_paid,
                "slippage_usd": o.slippage_usd,
                "is_taker": o.is_taker,
            })

        fills_out = []
        for t in self.paper_broker.trades:
            fills_out.append({
                "trade_id": t.trade_id,
                "order_id": t.order_id,
                "symbol": t.symbol,
                "venue": t.venue,
                "side": t.side.value,
                "price": t.price,
                "quantity": t.quantity,
                "fee": t.fee,
                "slippage_usd": t.slippage_usd,
                "timestamp_ns": t.timestamp_ns,
                "is_taker": t.is_taker,
            })

        return {
            "data_source": "MOCK" if self.mock_mode else "PAPER_SIMULATION",
            "status": "MOCK" if self.mock_mode else "RUNNING",
            "operational_state": "MOCK" if self.mock_mode else "RUNNING",
            "is_fixture": self.mock_mode,
            "state_kind": "PAPER",
            "is_own_capital": False,
            "persisted": False,
            "initial_cash_usd": self.paper_broker.initial_cash_usd,
            "cash_usd": self.paper_broker.cash_usd,
            "equity_usd": self.paper_broker.cash_usd,
            "realized_pnl_usd": sum(p.realized_pnl_usd for p in self.paper_broker.positions.values()),
            "unrealized_pnl_usd": 0.0,
            "simulated_latency_ms": self.paper_broker.simulated_latency_ms,
            "maker_fee_bps": self.paper_broker.maker_fee_bps,
            "taker_fee_bps": self.paper_broker.taker_fee_bps,
            "base_slippage_bps": self.paper_broker.base_slippage_bps,
            "positions": positions_out,
            "orders": orders_out,
            "fills": fills_out,
        }

    # --------------------------------------------------------------------------
    # Execution Domain & Reconciliation
    # --------------------------------------------------------------------------

    def get_execution_state(self) -> Dict[str, Any]:
        recon_data = ExecutionPlaneService.get_instance().get_reconciliation()
        recon_status = recon_data.get("status", "NOT_CONFIGURED")
        events_count = recon_data.get("reconciliation_events_count", 0)
        has_run = events_count > 0 and recon_status not in ("NOT_CONFIGURED", "UNKNOWN", "NOT_RUN")

        return {
            "execution_mode": "DRY_RUN_PAPER_SIMULATION",
            "live_execution_authority": False,
            "live_capital_authorized": 0.0,
            "reconciliation_status": recon_status if has_run else "NOT_RUN",
            "mismatch_detected": (recon_status == "MISMATCH") if has_run else None,
            "drift_usd": 0.0 if (has_run and recon_status == "HEALTHY") else None,
            "tracked_orders_count": len(self.lifecycle_tracker._intents),
            "orders": [],
            "provenance": {
                "source": "EXECUTION_PLANE",
                "reconciliation_events_count": events_count,
                "latest_event": recon_data.get("latest_event"),
            },
        }

    # --------------------------------------------------------------------------
    # Risk Engine & Kill Switches
    # --------------------------------------------------------------------------

    def get_risk_status(self) -> Dict[str, Any]:
        global_active = self.risk_engine.kill_switch_active or bool(self.execution_kill_switch._active.get(("GLOBAL", "")))
        return {
            **self._prov("LOCAL_RUNTIME"),
            "live_capital_state": "CAPITAL_LOCKED",
            "authorized_live_capital_usd": 0.0,
            "kill_switch_active": global_active,
            "kill_switch_reason": self.risk_engine.kill_switch_reason or ("Global kill switch active" if global_active else None),
            "current_equity_usd": self.risk_engine.current_equity_usd,
            "peak_equity_usd": self.risk_engine.peak_equity_usd,
            "current_drawdown_pct": self.risk_engine.current_drawdown_pct(),
            "limits": {
                "max_drawdown_limit_pct": self.risk_limits.max_drawdown_limit_pct,
                "drawdown_warning_pct": self.risk_limits.drawdown_warning_pct,
                "max_gross_leverage": self.risk_limits.max_gross_leverage,
                "max_single_position_pct": self.risk_limits.max_single_position_pct,
                "live_capital_locked": True,
            },
            "kill_switches": {
                "GLOBAL": {"active": global_active, "status": "LOCKED" if global_active else "ARMED", "persisted": True},
                "OWN_POCKET": {"active": any(k[0] == "ACCOUNT" and k[1] == "OWN_MAIN" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "PROP_POCKET": {"active": any(k[0] == "ACCOUNT" and k[1] == "PROP_ALPHA_100K" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "VENUE": {"active": any(k[0] == "VENUE" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "ACCOUNT": {"active": any(k[0] == "ACCOUNT" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "STRATEGY": {"active": any(k[0] == "STRATEGY" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "SYMBOL": {"active": any(k[0] == "SYMBOL" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "ASSET": {"active": any(k[0] == "SYMBOL" and v for k, v in self.execution_kill_switch._active.items()), "status": "ARMED", "persisted": True},
                "EVENT_CLUSTER": {"active": False, "status": "ARMED", "persisted": False},
            },
            "active_scopes": self.execution_kill_switch.active_scopes(),
            "recent_decisions": self.risk_decisions,
        }

    # --------------------------------------------------------------------------
    # Capital Pockets & Prop Profiles
    # --------------------------------------------------------------------------

    def get_capital_pockets(self) -> Dict[str, Any]:
        pockets_out = []
        for p in self.capital_pockets.values():
            pockets_out.append({
                "pocket_id": p.pocket_id,
                "pocket_type": p.pocket_type.value,
                "state_kind": "HYPOTHETICAL" if (not self.mock_mode and p.pocket_type == PocketType.OWN) else ("MOCK" if self.mock_mode else "NOT_CONFIGURED"),
                "firm_name": p.firm_name,
                "account_id": p.account_id,
                "initial_equity_usd": p.initial_equity_usd,
                "current_equity_usd": p.current_equity_usd,
                "peak_equity_usd": p.peak_equity_usd,
                "daily_starting_equity_usd": p.daily_starting_equity_usd,
                "daily_loss_limit_pct": p.daily_loss_limit_pct,
                "trailing_drawdown_limit_pct": p.trailing_drawdown_limit_pct,
                "is_frozen": p.is_frozen,
                "freeze_reason": p.freeze_reason,
            })
        return {
            "isolation_invariant": "Zero risk transfer: Prop account losses never impact Own capital limits.",
            **({"data_source": "MOCK", "status": "MOCK", "is_fixture": True} if self.mock_mode
               else {"data_source": "CONFIG", "status": "CONFIG_BASELINE", "is_fixture": False}),
            "provenance_note": "Own-capital baseline is USD 2,000 (HYPOTHETICAL, not live); live authorized USD 0." + (" Demo pockets are fixtures." if self.mock_mode else ""),
            "own_capital_baseline_usd": 2000.0,
            "own_capital_state_kind": "HYPOTHETICAL",
            "authorized_live_capital_usd": 0.0,
            "pockets": pockets_out,
        }

    def get_prop_profiles(self) -> List[Dict[str, Any]]:
        out = []
        for p in self.prop_profiles.values():
            row = p.model_dump()
            # Seeded demo providers are fictional fixtures, never operational/verified production state.
            row["data_source"] = "MOCK"
            row["status"] = "MOCK"
            row["is_fixture"] = True
            row["provenance_note"] = "DEMO FIXTURE: fictional provider; verification_status is NOT real evidence"
            out.append(row)
        return out

    def get_prop_simulator_result(self, strategy_id: str, provider_id: str) -> Dict[str, Any]:
        profile = self.prop_profiles.get(f"{provider_id}_v1") or self.prop_profiles.get(provider_id)
        if not profile and self.prop_profiles:
            profile = next(iter(self.prop_profiles.values()))
        if not profile:
            return {"status": "NOT_AVAILABLE", "data_source": "UNAVAILABLE",
                    "reason": f"No prop profile configured for provider {provider_id!r}"}

        # Simulate with 0 trades to show empirical fail-closed behavior
        return self.prop_simulator.simulate(
            strategy_id=strategy_id,
            profile=profile,
            trades=None,  # Insufficient empirical trades (<30)
        )

    # --------------------------------------------------------------------------
    # Audit Trail
    # --------------------------------------------------------------------------

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return sorted(self.audit_events, key=lambda x: x["timestamp_utc"], reverse=True)
