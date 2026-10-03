"""Performance Attribution and Multi-Factor PnL Decomposition endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/attribution", tags=["Attribution"])


@router.get("")
def get_attribution():
    """No attribution without real fills: MISSING != ZERO."""
    return {
        "status": "NOT_AVAILABLE",
        "data_source": "UNAVAILABLE",
        "reason": "No attributable realized trades; attribution is not computed from empty data",
        "benchmark_symbol": "BTCUSDT",
        "gross_pnl_usd": None,
        "net_pnl_usd": None,
        "alpha_pnl_usd": None,
        "beta_pnl_usd": None,
        "total_fees_usd": None,
        "total_slippage_usd": None,
        "implementation_shortfall_usd": None,
        "by_strategy": {},
        "by_regime": {},
    }
