"""Strategy Registry and candidate specification endpoints."""
from fastapi import APIRouter, HTTPException
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


@router.get("")
def list_strategies():
    svc = QuantOSDataService.get_instance()
    return svc.get_strategies()


@router.get("/str002/specialized")
def get_str002_specialized_view():
    svc = QuantOSDataService.get_instance()
    return svc.get_str002_specialized()


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str):
    svc = QuantOSDataService.get_instance()
    strat = svc.get_strategy_detail(strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found in registry")
    return strat
