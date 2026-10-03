"""Portfolio Selection Gates endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/gates", tags=["Portfolio Gates"])


@router.get("")
def get_gates():
    svc = QuantOSDataService.get_instance()
    return svc.get_gates_summary()


@router.get("/{strategy_id}")
def get_strategy_gates(strategy_id: str):
    svc = QuantOSDataService.get_instance()
    summary = svc.get_gates_summary()
    return {
        "strategy_id": strategy_id,
        "gates": summary.get("gates", []),
        "overall_status": "PENDING",
        "reason": f"Strategy '{strategy_id}' is in RESEARCH stage. Complete walk-forward backtest dataset required for gate evaluation.",
    }
