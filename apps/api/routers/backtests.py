"""Backtest explorer and validation replay endpoints."""
from fastapi import APIRouter, HTTPException, Request
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/backtests", tags=["Backtests"])


def _local_only(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")


@router.post("/str002/run")
def run_str002_replay(request: Request, days: float = 7.0, source: str = "recorded"):
    _local_only(request)
    from apps.api.services import replay_runner
    src = "history" if source == "history" else "recorded"
    return replay_runner.start(days=max(0.1, min(days, 180.0)), source=src)


@router.get("/str002/status")
def str002_replay_status():
    from apps.api.services import replay_runner
    return replay_runner.status()


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
