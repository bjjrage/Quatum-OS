"""ExecutionPlaneService: Read-only operational inspection service for Quant OS Execution Plane.

Invariants:
- All endpoints are strictly READ-ONLY (GET). No endpoint is capable of submitting or modifying orders.
- Effective mode is LIVE_LOCKED with $0 authorized live capital.
- Secrets are NEVER returned or exposed.
- Missing credentials or reconciliation state are honestly reported as NOT_CONFIGURED or UNKNOWN.
- Provenance vocabulary: REAL_RUNTIME, LOCAL_PERSISTED, CONFIG, DERIVED, PAPER_SIMULATION, SANDBOX, SHADOW, MOCK, UNAVAILABLE, UNKNOWN.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.execution_plane.adapters.real import BinanceUSDMAdapter, BybitAdapter, DeribitAdapter
from src.execution_plane.models import (
    DEFAULT_EXECUTION_MODE,
    ExecutionMode,
    not_configured_account,
    parse_mode,
)
from src.execution_plane.security import CONFIGURED, CredentialProvider
from src.execution_plane.store import ExecutionKillSwitch, ExecutionStore
from src.execution_plane.telemetry import aggregate_latency
from src.persistence.backend import LocalPersistenceBackend, PersistenceBackend


class ExecutionPlaneService:
    _instance: Optional["ExecutionPlaneService"] = None

    def __init__(
        self,
        backend: Optional[PersistenceBackend] = None,
        credentials: Optional[CredentialProvider] = None,
    ):
        self.backend = backend or LocalPersistenceBackend()
        self.store = ExecutionStore(self.backend)
        self.killswitch = ExecutionKillSwitch(self.backend)
        self.credentials = credentials or CredentialProvider()

        # Build real adapters with transport=None (no network; safe for capabilities / metadata inspection)
        self.adapters = {
            "binance_perp": BinanceUSDMAdapter(
                credentials=self.credentials, environment="LIVE", transport=None
            ),
            "bybit": BybitAdapter(
                credentials=self.credentials, environment="LIVE", transport=None
            ),
            "deribit": DeribitAdapter(
                credentials=self.credentials, environment="LIVE", transport=None
            ),
        }

    @classmethod
    def get_instance(cls) -> "ExecutionPlaneService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # ------------------------------------------------------------- status
    def get_status(self) -> Dict[str, Any]:
        configured_mode = parse_mode(os.environ.get("QUANT_OS_EXECUTION_MODE"))
        # Strict safety invariant: live capital is locked at $0
        authorized_live_capital_usd = 0.0
        effective_mode = ExecutionMode.LIVE_LOCKED.value

        venues_summary = {}
        for v, a in self.adapters.items():
            venues_summary[v] = {
                "environment": a.environment,
                "credentials_status": a._auth_status(),
                "order_submit_available": False,
                "live_available": False,
            }

        return {
            "data_source": "CONFIG",
            "configured_mode": configured_mode.value,
            "effective_mode": effective_mode,
            "live_trading_locked": True,
            "authorized_live_capital_usd": authorized_live_capital_usd,
            "own_capital_baseline_usd": 2000.0,
            "economic_edge_validated": False,
            "real_production_orders_sent": 0,
            "venues": venues_summary,
            "safety_invariants": {
                "risk_veto_override_possible": False,
                "withdrawal_permission_required": False,
                "secrets_in_storage": False,
                "sandbox_live_isolation": True,
            },
        }

    # ------------------------------------------------------------- venues
    def get_venues(self) -> List[Dict[str, Any]]:
        result = []
        for v, a in self.adapters.items():
            caps = a.capabilities()
            h = a.health()
            result.append({
                "venue": v,
                "environment": a.environment,
                "health": h,
                "capabilities": caps,
                "credentials_status": a._auth_status(),
            })
        return result

    # ------------------------------------------------------------- orders
    def get_orders(self) -> List[Dict[str, Any]]:
        orders = self.store.list_orders()
        return [o.summary() for o in orders]

    # ------------------------------------------------------------- fills
    def get_fills(self) -> List[Dict[str, Any]]:
        return self.store.fills()

    # ------------------------------------------------------------- reconciliation
    def get_reconciliation(self, venue: Optional[str] = None) -> Dict[str, Any]:
        events = self.store.recon_events(venue)
        if not events:
            return {
                "status": "NOT_CONFIGURED" if not any(
                    self.credentials.is_configured(v) for v in self.adapters
                ) else "UNKNOWN",
                "live_trading_locked": True,
                "reconciliation_events_count": 0,
                "events": [],
                "description": "No reconciliation executed. Production reconciliation state is fail-closed.",
                "data_source": "LOCAL_PERSISTED",
            }
        latest = events[-1]
        return {
            "status": latest.get("status", "UNKNOWN"),
            "live_trading_locked": True,
            "reconciliation_events_count": len(events),
            "latest_event": latest,
            "events": events[-10:],
            "data_source": "LOCAL_PERSISTED",
        }

    # ------------------------------------------------------------- latency
    def get_latency(self) -> Dict[str, Any]:
        samples = self.store.latency_samples()
        return aggregate_latency(samples)

    # ------------------------------------------------------------- credentials
    def get_credentials_status(self) -> Dict[str, Any]:
        status_by_venue = {}
        for v in ("binance_perp", "bybit", "deribit"):
            live_st = self.credentials.status(v, "LIVE")
            sbx_st = self.credentials.status(v, "SANDBOX")
            status_by_venue[v] = {
                "LIVE": live_st,
                "SANDBOX": sbx_st,
            }
        return {
            "venues": status_by_venue,
            "withdrawal_permission_required": False,
            "secrets_exposed": False,
            "data_source": "CONFIG",
        }

    # ------------------------------------------------------------- account status
    def get_account_status(self, venue: str) -> Dict[str, Any]:
        snap = self.store.latest_account_snapshot(venue)
        if snap is not None:
            return snap
        # Honest fallback: unconfigured account
        return not_configured_account(venue).model_dump()

    # ------------------------------------------------------------- kill switches
    def get_kill_switches(self) -> Dict[str, Any]:
        return {
            "active_scopes": self.killswitch.active_scopes(),
            "data_source": "LOCAL_PERSISTED",
        }
