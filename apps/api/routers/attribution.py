"""Performance Attribution and Multi-Factor PnL Decomposition endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/attribution", tags=["Attribution"])


@router.get("")
def get_attribution():
    return {
        "status": "AVAILABLE",
        "benchmark_symbol": "BTCUSDT",
        "gross_pnl_usd": 0.0,
        "net_pnl_usd": 0.0,
        "alpha_pnl_usd": 0.0,
        "beta_pnl_usd": 0.0,
        "total_fees_usd": 0.0,
        "total_slippage_usd": 0.0,
        "implementation_shortfall_usd": 0.0,
        "by_strategy": {
            "STR-001": {"gross_pnl": 0.0, "net_pnl": 0.0, "alpha": 0.0, "beta": 0.0, "trades": 0},
            "STR-002": {"gross_pnl": 0.0, "net_pnl": 0.0, "alpha": 0.0, "beta": 0.0, "trades": 0},
            "STR-003": {"gross_pnl": 0.0, "net_pnl": 0.0, "alpha": 0.0, "beta": 0.0, "trades": 0},
            "STR-PUMP-COPY": {"gross_pnl": 0.0, "net_pnl": 0.0, "alpha": 0.0, "beta": 0.0, "trades": 0},
        },
        "by_regime": {
            "NORMAL": {"gross_pnl": 0.0, "trades": 0},
            "HIGH_VOLATILITY": {"gross_pnl": 0.0, "trades": 0},
            "STRESS": {"gross_pnl": 0.0, "trades": 0},
        },
    }
