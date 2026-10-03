"""Backtest explorer and validation replay endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/backtests", tags=["Backtests"])


@router.get("")
def list_backtests():
    # Real Quant OS backtests are produced in research pipelines.
    # When no historical backtest is written to disk, return explicit NOT_AVAILABLE state
    return {
        "status": "NOT_AVAILABLE",
        "reason": "Deterministic Backtest Engine available in src/backtest/engine.py; no persisted runs in active directory.",
        "runs": [],
        "available_strategies": ["STR-001", "STR-002", "STR-003", "STR-PUMP-COPY"],
        "cost_models": ["v1_taker_5bps", "v2_maker_taker_tier1"],
    }


@router.get("/{run_id}")
def get_backtest_run(run_id: str):
    return {
        "status": "NOT_AVAILABLE",
        "run_id": run_id,
        "reason": f"Backtest run '{run_id}' not found.",
    }
