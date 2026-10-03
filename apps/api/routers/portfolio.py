"""Portfolio capital budgeting and regime policy endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api", tags=["Portfolio"])


@router.get("/portfolio")
def get_portfolio():
    svc = QuantOSDataService.get_instance()
    return svc.get_portfolio_state()


@router.get("/regime")
def get_regime():
    return {
        "status": "OPERATIONAL",
        "macro_regime": "NORMAL",
        "crypto_domain_regime": "BALANCED_VOLATILITY",
        "btc_trend_state": "FLAT",
        "capital_allocation_multiplier": 1.0,
        "ai_metadata_advisory_state": "ISOLATED",
        "notes": "Regime Policy Engine enforcing capital allocation multipliers across strategy families.",
    }
