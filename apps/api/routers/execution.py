"""Execution Plane read-only operational endpoints for Quant OS.

Invariants:
- ALL endpoints are strictly HTTP GET (read-only).
- No endpoint is capable of submitting or modifying orders.
- Secrets are NEVER returned.
- Live capital is locked at $0.
- Missing credentials or reconciliation state are reported honestly as NOT_CONFIGURED or UNKNOWN.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from apps.api.services.data_service import QuantOSDataService
from src.execution_plane.service import ExecutionPlaneService

router = APIRouter(prefix="/api/execution", tags=["Execution"])


@router.get("/status")
def get_execution_status() -> Dict[str, Any]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_status()


@router.get("/venues")
def get_execution_venues() -> List[Dict[str, Any]]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_venues()


@router.get("/orders")
def get_execution_orders() -> List[Dict[str, Any]]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_orders()


@router.get("/fills")
def get_execution_fills() -> List[Dict[str, Any]]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_fills()


@router.get("/reconciliation")
def get_reconciliation(venue: Optional[str] = Query(None)) -> Dict[str, Any]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_reconciliation(venue)


@router.get("/latency")
def get_latency_report() -> Dict[str, Any]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_latency()


@router.get("/credentials/status")
def get_credentials_status() -> Dict[str, Any]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_credentials_status()


@router.get("/account-status")
def get_account_status(venue: str = Query("binance_perp")) -> Dict[str, Any]:
    svc = ExecutionPlaneService.get_instance()
    return svc.get_account_status(venue)


@router.get("/intents")
def get_execution_intents() -> List[Dict[str, Any]]:
    # Retain backward compatibility for older lifecycle tracker while adding canonical store intents
    svc = QuantOSDataService.get_instance()
    tracker = svc.lifecycle_tracker
    intents = []
    for i_id, intent in tracker._intents.items():
        state = tracker.get_state(i_id)
        intents.append({
            "order_intent_id": intent.order_intent_id,
            "strategy_id": intent.strategy_id,
            "symbol": intent.symbol,
            "venue": intent.venue,
            "side": intent.side,
            "order_type": intent.order_type,
            "state": state.value if state else "UNKNOWN",
        })
    return intents
