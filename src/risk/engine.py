"""
Deterministic Pre-Trade and Post-Trade Risk Engine.

Invariants:
- Absolute veto authority over all orders.
- Zero Live Capital enforcement while locked.
- Portfolio drawdown circuit breaker (hard stop prevents new risk).
- Gross leverage ceiling.
- Single asset and EventCluster exposure caps.
- High-frequency burst rate limiter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Dict, Any, List, Optional, Tuple

from src.risk.event_cluster import EventCluster


class RiskViolationCode(str, Enum):
    NONE = "NONE"
    CAPITAL_LOCKED = "CAPITAL_LOCKED"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    INVALID_ORDER = "INVALID_ORDER"
    BURST_RATE_LIMIT_EXCEEDED = "BURST_RATE_LIMIT_EXCEEDED"
    MAX_DRAWDOWN_EXCEEDED = "MAX_DRAWDOWN_EXCEEDED"
    GROSS_LEVERAGE_EXCEEDED = "GROSS_LEVERAGE_EXCEEDED"
    SINGLE_ASSET_CONCENTRATION_EXCEEDED = "SINGLE_ASSET_CONCENTRATION_EXCEEDED"
    EVENT_CLUSTER_LIMIT_EXCEEDED = "EVENT_CLUSTER_LIMIT_EXCEEDED"


@dataclass
class ProposedOrder:
    order_id: str
    strategy_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    price: float
    venue: str = ""
    timestamp_s: Optional[float] = None


@dataclass
class RiskDecision:
    approved: bool
    violation_code: RiskViolationCode = RiskViolationCode.NONE
    reason: str = "Approved"
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskLimits:
    max_drawdown_limit_pct: float = 0.10  # 10% hard stop
    drawdown_warning_pct: float = 0.05   # 5% warning
    max_gross_leverage: float = 3.0       # Max Gross Notional / Equity
    max_single_position_pct: float = 0.25 # Max single asset notional / Equity
    max_orders_per_window: int = 20       # Burst rate limiter max orders
    rate_limit_window_seconds: float = 1.0
    live_capital_locked: bool = True     # Strict $0 live risk invariant


class DeterministicRiskEngine:
    """
    Deterministic Risk Gate enforcing all portfolio, exchange, and cluster limits.
    """

    def __init__(
        self,
        initial_equity_usd: float = 100_000.0,
        limits: Optional[RiskLimits] = None,
    ):
        self.limits = limits or RiskLimits()
        self.initial_equity_usd = initial_equity_usd
        self.peak_equity_usd = initial_equity_usd
        self.current_equity_usd = initial_equity_usd

        self.positions: Dict[str, float] = {}  # symbol -> net qty
        self.mark_prices: Dict[str, float] = {}  # symbol -> price
        self.event_clusters: Dict[str, EventCluster] = {}

        self.kill_switch_active: bool = False
        self.kill_switch_reason: Optional[str] = None
        self.order_timestamps: List[float] = []

    def register_event_cluster(self, cluster: EventCluster) -> None:
        self.event_clusters[cluster.cluster_id] = cluster

    def trigger_kill_switch(self, reason: str) -> None:
        self.kill_switch_active = True
        self.kill_switch_reason = reason

    def reset_kill_switch(self) -> None:
        self.kill_switch_active = False
        self.kill_switch_reason = None

    def update_portfolio_state(
        self,
        equity_usd: float,
        positions: Optional[Dict[str, float]] = None,
        mark_prices: Optional[Dict[str, float]] = None,
    ) -> None:
        self.current_equity_usd = equity_usd
        if equity_usd > self.peak_equity_usd:
            self.peak_equity_usd = equity_usd

        if positions is not None:
            self.positions = dict(positions)
        if mark_prices is not None:
            self.mark_prices = dict(mark_prices)

    def current_drawdown_pct(self) -> float:
        if self.peak_equity_usd <= 0.0:
            return 0.0
        return max(0.0, (self.peak_equity_usd - self.current_equity_usd) / self.peak_equity_usd)

    def current_gross_notional(self) -> float:
        gross = 0.0
        for sym, qty in self.positions.items():
            price = self.mark_prices.get(sym, 0.0)
            gross += abs(qty * price)
        return gross

    def evaluate_order(
        self,
        order: ProposedOrder,
        is_live: bool = False,
        current_time_s: Optional[float] = None,
    ) -> RiskDecision:
        """
        Evaluate order against all deterministic risk invariants.
        Returns RiskDecision.
        """
        eval_time = current_time_s if current_time_s is not None else (order.timestamp_s or time.time())

        # 1. Live Capital Lock Enforcement
        if is_live and self.limits.live_capital_locked:
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.CAPITAL_LOCKED,
                reason="Live capital is locked ($0 Live Risk policy). Orders cannot be sent to live market.",
            )

        # 2. Kill Switch Check
        if self.kill_switch_active:
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.KILL_SWITCH_ACTIVE,
                reason=f"Emergency Kill Switch is active: {self.kill_switch_reason}",
            )

        # 3. Basic Order Validity
        if order.quantity <= 0 or order.price <= 0:
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.INVALID_ORDER,
                reason=f"Order quantity ({order.quantity}) and price ({order.price}) must be positive.",
            )

        side_sign = 1.0 if order.side.upper() == "BUY" else -1.0
        delta_qty = side_sign * order.quantity
        curr_qty = self.positions.get(order.symbol, 0.0)
        new_qty = curr_qty + delta_qty

        # Check if this order strictly reduces current risk / position
        is_risk_reducing = (curr_qty > 0 and delta_qty < 0 and new_qty >= 0) or \
                            (curr_qty < 0 and delta_qty > 0 and new_qty <= 0)

        # 4. Burst Rate Limiter
        # Prune old timestamps
        cutoff = eval_time - self.limits.rate_limit_window_seconds
        self.order_timestamps = [t for t in self.order_timestamps if t >= cutoff]
        if len(self.order_timestamps) >= self.limits.max_orders_per_window:
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.BURST_RATE_LIMIT_EXCEEDED,
                reason=(
                    f"Burst rate limit breached: {len(self.order_timestamps)} orders in "
                    f"{self.limits.rate_limit_window_seconds}s (limit: {self.limits.max_orders_per_window})"
                ),
            )

        # 5. Drawdown Circuit Breaker
        dd = self.current_drawdown_pct()
        if dd >= self.limits.max_drawdown_limit_pct:
            if not is_risk_reducing:
                return RiskDecision(
                    approved=False,
                    violation_code=RiskViolationCode.MAX_DRAWDOWN_EXCEEDED,
                    reason=(
                        f"Portfolio drawdown ({dd*100:.2f}%) exceeds hard circuit breaker "
                        f"({self.limits.max_drawdown_limit_pct*100:.2f}%). Only risk-reducing orders permitted."
                    ),
                    metrics={"drawdown_pct": dd},
                )

        # 6. Single Asset Concentration Cap
        new_asset_notional = abs(new_qty * order.price)
        max_allowed_single = self.current_equity_usd * self.limits.max_single_position_pct
        if new_asset_notional > max_allowed_single and not is_risk_reducing:
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.SINGLE_ASSET_CONCENTRATION_EXCEEDED,
                reason=(
                    f"Asset {order.symbol} notional ${new_asset_notional:,.2f} exceeds "
                    f"{self.limits.max_single_position_pct*100:.1f}% equity cap (${max_allowed_single:,.2f})"
                ),
                metrics={"new_notional": new_asset_notional, "limit": max_allowed_single},
            )

        # 7. Gross Leverage Ceiling
        simulated_positions = dict(self.positions)
        simulated_positions[order.symbol] = new_qty
        simulated_prices = dict(self.mark_prices)
        simulated_prices[order.symbol] = order.price

        simulated_gross = 0.0
        for s, q in simulated_positions.items():
            p = simulated_prices.get(s, 0.0)
            simulated_gross += abs(q * p)

        if self.current_equity_usd > 0:
            simulated_leverage = simulated_gross / self.current_equity_usd
            if simulated_leverage > self.limits.max_gross_leverage and not is_risk_reducing:
                return RiskDecision(
                    approved=False,
                    violation_code=RiskViolationCode.GROSS_LEVERAGE_EXCEEDED,
                    reason=(
                        f"Gross leverage {simulated_leverage:.2f}x exceeds ceiling "
                        f"{self.limits.max_gross_leverage:.2f}x"
                    ),
                    metrics={"gross_leverage": simulated_leverage, "limit": self.limits.max_gross_leverage},
                )

        # 8. EventCluster Caps
        for cluster_id, cluster in self.event_clusters.items():
            if cluster.is_member(order.symbol):
                allowed, cluster_reason = cluster.check_proposed_order(
                    symbol=order.symbol,
                    delta_qty=delta_qty,
                    price=order.price,
                    current_positions=self.positions,
                    mark_prices=self.mark_prices,
                )
                if not allowed and not is_risk_reducing:
                    return RiskDecision(
                        approved=False,
                        violation_code=RiskViolationCode.EVENT_CLUSTER_LIMIT_EXCEEDED,
                        reason=cluster_reason or f"EventCluster '{cluster_id}' breached",
                        metrics={"cluster_id": cluster_id},
                    )

        # Order passed all deterministic checks
        self.order_timestamps.append(eval_time)
        return RiskDecision(
            approved=True,
            violation_code=RiskViolationCode.NONE,
            reason="Approved by Deterministic Risk Engine",
            metrics={"drawdown_pct": dd, "is_risk_reducing": is_risk_reducing},
        )
