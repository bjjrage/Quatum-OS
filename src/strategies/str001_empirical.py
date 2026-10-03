"""STR-001: Polymarket x Deribit Relative Value Empirical Pipeline."""
import math
from typing import Dict, Any, Optional

from .factory import CandidateHypothesis, Signal, SignalDirection
from .models import StrategySpec, StrategyFamily, StrategyOrigin, StrategyStage
from src.quant.digital_probability import digital_call_prob_analytic


class STR001RelativeValueAlpha(CandidateHypothesis):
    """STR-001 Relative Value Alpha between Polymarket binary contract and Deribit options."""

    def __init__(
        self,
        min_edge_bps: float = 200.0,      # 2% mispricing minimum hurdle
        poly_fee_bps: float = 50.0,       # Polymarket taker fee / gas buffer
        deribit_fee_bps: float = 30.0,     # Deribit option transaction fee
        slippage_buffer_bps: float = 20.0,
    ):
        spec = StrategySpec(
            strategy_id="STR-001",
            family=StrategyFamily.RELATIVE_VALUE,
            origin=StrategyOrigin.QUANT,
            stage=StrategyStage.RESEARCH,
            name="Polymarket x Deribit Relative Value Arbitrage",
            description="Empirical relative value between binary prediction markets and option-implied probability surfaces",
            parameters={
                "min_edge_bps": min_edge_bps,
                "poly_fee_bps": poly_fee_bps,
                "deribit_fee_bps": deribit_fee_bps,
                "slippage_buffer_bps": slippage_buffer_bps,
            },
        )
        super().__init__(spec)
        self.min_edge_bps = min_edge_bps
        self.total_hurdle_bps = poly_fee_bps + deribit_fee_bps + slippage_buffer_bps

    def generate_signal(self, market_data: Dict[str, Any], current_ts_ns: int) -> Optional[Signal]:
        """Evaluate Polymarket price against Deribit risk-neutral probability surface."""
        # Required pricing inputs
        poly_price = market_data.get("polymarket_mid_price")
        F = market_data.get("deribit_forward_price")
        K = market_data.get("strike_price")
        T = market_data.get("time_to_expiry_years")
        sigma = market_data.get("implied_volatility")
        dsigma_dK = market_data.get("dsigma_dK", 0.0)

        if None in (poly_price, F, K, T, sigma) or T <= 0.0 or sigma <= 0.0:
            return None

        # Calculate exact risk-neutral probability with skew
        p_rn = digital_call_prob_analytic(
            F=float(F),
            K=float(K),
            T=float(T),
            sigma=float(sigma),
            dsigma_dK=float(dsigma_dK),
        )

        # Mispricing spread in probability units
        spread = float(poly_price) - p_rn
        spread_bps = spread * 10000.0

        net_edge_bps = abs(spread_bps) - self.total_hurdle_bps

        if net_edge_bps <= 0.0 or abs(spread_bps) < self.min_edge_bps:
            return None

        # Sizing proportional to net edge
        confidence = min(1.0, net_edge_bps / 500.0)
        target_weight = min(0.20, net_edge_bps / 2000.0)

        direction = SignalDirection.SHORT if spread > 0 else SignalDirection.LONG

        return Signal(
            strategy_id=self.spec.strategy_id,
            symbol=market_data.get("symbol", "BTC-POLY-DERIBIT"),
            venue="polymarket",
            direction=direction,
            target_weight=round(target_weight, 4),
            confidence=round(confidence, 4),
            expected_edge_bps=round(net_edge_bps, 2),
            ts_ns=current_ts_ns,
            metadata={
                "poly_price": round(float(poly_price), 4),
                "deribit_rn_prob": round(p_rn, 4),
                "gross_spread_bps": round(spread_bps, 2),
                "net_edge_bps": round(net_edge_bps, 2),
                "dsigma_dK": dsigma_dK,
            },
        )
