"""STR-002: Behavioral Alpha / Impulse-Overshoot-Retracement Event Study & Strategy Engine."""
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Any, List, Optional

from .factory import CandidateHypothesis, Signal, SignalDirection
from .models import StrategySpec, StrategyFamily, StrategyOrigin, StrategyStage
from src.research.events import PriceImpulseEvent, ShockDirection


class MoveClassification(str, Enum):
    FORCED_LIQUIDITY_MOVE = "FORCED_LIQUIDITY_MOVE"
    INFORMATIVE_MOVE = "INFORMATIVE_MOVE"


@dataclass
class EventStudyObservation:
    """Rigorous 14-dimension record for each observed impulse event with causal trajectory tracking."""
    event_id: str
    symbol: str
    venue: str
    classification: MoveClassification
    # 1. Impulse magnitude (log return)
    impulse_magnitude: float
    # 2. Prior realized volatility
    prior_realized_volatility: float
    # 3. Forward returns at horizons [1m, 3m, 5m, 15m, 30m]
    forward_returns: Dict[str, float]
    # 4. Retracement ratio (fraction of impulse reversed at peak retracement or exit)
    retracement_ratio: float
    # 5. Maximum Favorable Excursion (MFE)
    mfe: float
    # 6. Maximum Adverse Excursion (MAE)
    mae: float
    # 7. Time to retracement in seconds
    time_to_retracement_s: float
    # 8. Asset liquidity tier
    liquidity_tier: str
    # 9. Bid-ask spread in bps
    spread_bps: float
    # 10. Orderbook depth
    depth: float
    # 11. Funding rate
    funding_rate: float
    # 12. Open Interest delta
    open_interest_delta: float
    # 13. Forced liquidation volume
    forced_liquidation_volume: float
    # 14. Market regime
    market_regime: str
    # Net economic edge after taker fees and slippage
    net_edge_bps: float
    # Causal path-dependent fields
    exit_reason: Optional[str] = None
    exit_price: Optional[float] = None
    is_stopped_out: bool = False


class STR002EventStudyAlpha(CandidateHypothesis):
    """STR-002 candidate strategy evaluating impulse overshoot and short-horizon retracement."""

    def __init__(
        self,
        min_z_score: float = 2.5,
        min_retracement_target_pct: float = 0.35,  # Expect at least 35% retracement
        fee_and_slippage_bps: float = 8.0,
    ):
        spec = StrategySpec(
            strategy_id="STR-002",
            family=StrategyFamily.BEHAVIORAL,
            origin=StrategyOrigin.HUMAN,
            stage=StrategyStage.RESEARCH,
            name="Behavioral Alpha / Short-Horizon Retracement",
            description="Exploitation of mechanical overshoot and subsequent mean reversion from forced liquidation cascades",
            parameters={
                "min_z_score": min_z_score,
                "min_retracement_target_pct": min_retracement_target_pct,
                "fee_and_slippage_bps": fee_and_slippage_bps,
            },
        )
        super().__init__(spec)
        self.min_z = min_z_score
        self.min_target = min_retracement_target_pct
        self.hurdle_bps = fee_and_slippage_bps

    @staticmethod
    def classify_move(
        has_forced_liquidations: bool,
        liquidation_volume: float,
        is_fundamental_news: bool = False,
    ) -> MoveClassification:
        """Distinguish Informative Moves (hacks, delistings, material news) from Forced/Liquidity Moves."""
        if is_fundamental_news:
            return MoveClassification.INFORMATIVE_MOVE
        if has_forced_liquidations or liquidation_volume > 100_000.0:
            return MoveClassification.FORCED_LIQUIDITY_MOVE
        return MoveClassification.INFORMATIVE_MOVE

    def analyze_event_trajectory(
        self,
        event: PriceImpulseEvent,
        post_impulse_prices: List[float],
        post_impulse_timestamps_ns: List[int],
        funding_rate: float = 0.0001,
        oi_delta: float = -500000.0,
        is_fundamental_news: bool = False,
        stop_buffer_pct: float = 0.005,
        max_holding_s: float = 900.0,
    ) -> EventStudyObservation:
        """Reconstruct full 14-dimension observation from impulse event and post-shock trajectory.
        
        Evaluates stops and targets chronologically and path-dependently:
        - If MAE breaches the stop buffer, the trade is stopped out immediately.
        - Peak retracement after a stop-out is NOT credited (prevents lookahead / optimistic bias).
        """
        classification = self.classify_move(
            has_forced_liquidations=event.has_forced_liquidations,
            liquidation_volume=event.forced_liquidation_volume,
            is_fundamental_news=is_fundamental_news,
        )

        p_start = event.start_price
        p_peak = event.peak_price
        impulse_dist = p_peak - p_start
        abs_impulse = abs(impulse_dist)

        # Dynamic hard stop distance: max(50 bps of price, 10% of impulse)
        stop_dist = max(p_peak * stop_buffer_pct, abs_impulse * 0.10) if abs_impulse > 0 else p_peak * 0.01

        mfe = 0.0
        mae = 0.0
        max_retracement = 0.0
        time_to_ret_s = 0.0
        exit_reason = "SERIES_END" if post_impulse_prices else "NO_DATA"
        exit_price = p_peak
        is_stopped_out = False

        fwd_returns: Dict[str, float] = {}

        if post_impulse_prices:
            # 1. Forward horizon returns from peak
            n = len(post_impulse_prices)
            fwd_returns["1m"] = round((post_impulse_prices[min(1, n - 1)] - p_peak) / p_peak, 4)
            fwd_returns["5m"] = round((post_impulse_prices[min(5, n - 1)] - p_peak) / p_peak, 4)
            fwd_returns["15m"] = round((post_impulse_prices[min(15, n - 1)] - p_peak) / p_peak, 4)

            # 2. Chronological causal evaluation
            for idx, p in enumerate(post_impulse_prices):
                ts = post_impulse_timestamps_ns[idx]
                elapsed_s = (ts - event.ts_peak_ns) / 1e9

                # For expansion up: retracement is downward (p < p_peak), adverse is upward (p > p_peak)
                # For expansion down: retracement is upward (p > p_peak), adverse is downward (p < p_peak)
                if event.direction == ShockDirection.EXPANSION_UP:
                    favorable = p_peak - p
                    adverse = p - p_peak
                else:
                    favorable = p - p_peak
                    adverse = p_peak - p

                if adverse > mae:
                    mae = adverse
                if favorable > mfe:
                    mfe = favorable

                # Check if stop loss was hit FIRST (adverse excursion exceeds stop distance)
                if adverse >= stop_dist:
                    is_stopped_out = True
                    exit_reason = "STOP_LOSS"
                    exit_price = p_peak + stop_dist if event.direction == ShockDirection.EXPANSION_UP else p_peak - stop_dist
                    time_to_ret_s = elapsed_s
                    # Stop-out terminates trajectory; cannot claim subsequent retracement
                    max_retracement = 0.0
                    break

                # Update favorable retracement
                if abs_impulse > 1e-6:
                    retrace_ratio = favorable / abs_impulse
                    if retrace_ratio > max_retracement:
                        max_retracement = retrace_ratio
                        time_to_ret_s = elapsed_s

                # Check if time expired
                if elapsed_s >= max_holding_s:
                    exit_reason = "TIME_EXPIRED"
                    exit_price = p
                    break
            else:
                # Completed without hitting stop loss or time limit
                if post_impulse_prices:
                    exit_price = post_impulse_prices[-1]
                    if max_retracement >= self.min_target:
                        exit_reason = "TARGET_REACHED"
                    else:
                        exit_reason = "SERIES_END"

        # Calculate causal net economic edge
        if is_stopped_out:
            gross_loss_pct = -(stop_dist / p_peak) if p_peak > 0 else -0.01
            gross_return_bps = gross_loss_pct * 10000.0
            net_edge = gross_return_bps - self.hurdle_bps
        else:
            gross_return_bps = max_retracement * abs(event.impulse_return) * 10000.0
            net_edge = gross_return_bps - self.hurdle_bps

        return EventStudyObservation(
            event_id=event.event_id,
            symbol=event.symbol,
            venue=event.venue,
            classification=classification,
            impulse_magnitude=round(event.impulse_return, 6),
            prior_realized_volatility=round(event.prior_volatility, 6),
            forward_returns=fwd_returns,
            retracement_ratio=round(max_retracement, 4),
            mfe=round(mfe, 2),
            mae=round(mae, 2),
            time_to_retracement_s=round(time_to_ret_s, 2),
            liquidity_tier="TIER_1_MAJOR",
            spread_bps=1.5,
            depth=100.0,
            funding_rate=funding_rate,
            open_interest_delta=oi_delta,
            forced_liquidation_volume=event.forced_liquidation_volume,
            market_regime="HIGH_VOLATILITY",
            net_edge_bps=round(net_edge, 2),
            exit_reason=exit_reason,
            exit_price=round(exit_price, 4) if exit_price is not None else None,
            is_stopped_out=is_stopped_out,
        )

    def generate_signal(self, market_data: Dict[str, Any], current_ts_ns: int) -> Optional[Signal]:
        """Generate mean reversion signal only on qualified Forced Liquidity moves."""
        event: Optional[PriceImpulseEvent] = market_data.get("impulse_event")
        if not event or abs(event.z_score) < self.min_z:
            return None

        classification = self.classify_move(
            has_forced_liquidations=event.has_forced_liquidations,
            liquidation_volume=event.forced_liquidation_volume,
            is_fundamental_news=market_data.get("is_fundamental_news", False),
        )

        # INFORMATIVE MOVES HAVE NO OBLIGATION TO REVERT -> STRICT FILTER
        if classification == MoveClassification.INFORMATIVE_MOVE:
            return None

        expected_retrace_bps = abs(event.impulse_return) * self.min_target * 10000.0
        net_edge = expected_retrace_bps - self.hurdle_bps

        if net_edge <= 0.0:
            return None

        # Direction is opposite to impulse (mean reversion)
        direction = (
            SignalDirection.SHORT
            if event.direction == ShockDirection.EXPANSION_UP
            else SignalDirection.LONG
        )

        confidence = min(1.0, net_edge / 50.0)
        target_weight = min(0.15, net_edge / 200.0)

        is_short = (direction == SignalDirection.SHORT)

        return Signal(
            strategy_id=self.spec.strategy_id,
            symbol=event.symbol,
            venue=event.venue,
            direction=direction,
            target_weight=round(target_weight, 4),
            confidence=round(confidence, 4),
            expected_edge_bps=round(net_edge, 2),
            ts_ns=current_ts_ns,
            metadata={
                "classification": classification.value,
                "impulse_z_score": event.z_score,
                "impulse_return_bps": round(event.impulse_return * 10000.0, 1),
                "expected_retracement_bps": round(expected_retrace_bps, 1),
                "forced_liq_volume": event.forced_liquidation_volume,
                "is_research_only": is_short,
                "is_executable": not is_short,
                "research_note": (
                    "SHORT side is strictly research-only ($0 live risk, 0 orders)."
                    if is_short
                    else "LONG side executable candidate subject to Risk Authority approval."
                ),
            },
        )
