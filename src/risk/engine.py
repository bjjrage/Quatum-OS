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


@dataclass(frozen=True)
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
        auto_register_in_flight: bool = False,
    ):
        self.limits = limits or RiskLimits()
        self.initial_equity_usd = initial_equity_usd
        self.peak_equity_usd = initial_equity_usd
        self.current_equity_usd = initial_equity_usd
        self.auto_register_in_flight = auto_register_in_flight

        self.positions: Dict[str, float] = {}  # symbol -> net qty
        self.mark_prices: Dict[str, float] = {}  # symbol -> price
        self.event_clusters: Dict[str, EventCluster] = {}
        self.in_flight_orders: Dict[str, ProposedOrder] = {}

        self.kill_switch_active: bool = False
        self.kill_switch_reason: Optional[str] = None
        self.order_timestamps: List[float] = []

    def register_in_flight(self, order: ProposedOrder) -> None:
        """Register an order currently in-flight / pending execution."""
        self.in_flight_orders[order.order_id] = order

    def release_in_flight(self, order_id: str) -> None:
        """Release an in-flight order when filled, cancelled, or rejected."""
        self.in_flight_orders.pop(order_id, None)

    def clear_in_flight(self) -> None:
        """Clear all in-flight orders."""
        self.in_flight_orders.clear()

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
        if not math.isfinite(equity_usd):
            raise ValueError(f"Invalid non-finite equity: {equity_usd}")
        self.current_equity_usd = equity_usd
        if equity_usd > self.peak_equity_usd:
            self.peak_equity_usd = equity_usd

        if positions is not None:
            self.positions = dict(positions)
        if mark_prices is not None:
            self.mark_prices = dict(mark_prices)

    def current_drawdown_pct(self) -> float:
        if self.peak_equity_usd <= 0.0 or not math.isfinite(self.current_equity_usd):
            return 1.0
        return max(0.0, (self.peak_equity_usd - self.current_equity_usd) / self.peak_equity_usd)

    def current_gross_notional(self) -> float:
        gross = 0.0
        for sym, qty in self.positions.items():
            if abs(qty) > 1e-9:
                price = self.mark_prices.get(sym)
                if price is None or not math.isfinite(price) or price <= 0.0:
                    raise ValueError(f"Missing or invalid mark price for open position in '{sym}'")
                gross += abs(qty * price)
        return gross

    def evaluate_order(
        self,
        order: ProposedOrder,
        is_live: bool = False,
        current_time_s: Optional[float] = None,
        auto_register_in_flight: Optional[bool] = None,
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

        # 3. Input Sanitization & Basic Order Validity (fail-closed on NaN / Inf / non-positive)
        if (
            not isinstance(order.quantity, (int, float))
            or not math.isfinite(order.quantity)
            or order.quantity <= 0
            or not isinstance(order.price, (int, float))
            or not math.isfinite(order.price)
            or order.price <= 0
        ):
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.INVALID_ORDER,
                reason=f"Order quantity ({order.quantity}) and price ({order.price}) must be positive finite numbers.",
            )

        side_str = order.side.upper() if isinstance(order.side, str) else ""
        if side_str not in ("BUY", "SELL"):
            return RiskDecision(
                approved=False,
                violation_code=RiskViolationCode.INVALID_ORDER,
                reason=f"Invalid order side '{order.side}'. Must be strictly 'BUY' or 'SELL'.",
            )

        side_sign = 1.0 if side_str == "BUY" else -1.0
        delta_qty = side_sign * order.quantity
        curr_qty = self.positions.get(order.symbol, 0.0)
        new_qty = curr_qty + delta_qty

        # Check if this order strictly reduces current risk / position
        is_risk_reducing = (curr_qty > 0 and delta_qty < 0 and new_qty >= 0) or \
                            (curr_qty < 0 and delta_qty > 0 and new_qty <= 0)

        # Missing mark price validation for open positions (fail-closed if holding open positions without mark price)
        for s, q in self.positions.items():
            if abs(q) > 1e-9:
                p = self.mark_prices.get(s)
                if p is None or not math.isfinite(p) or p <= 0.0:
                    if not is_risk_reducing or s != order.symbol:
                        return RiskDecision(
                            approved=False,
                            violation_code=RiskViolationCode.INVALID_ORDER,
                            reason=f"Missing or non-positive mark price for open position in '{s}'.",
                        )

        # Non-positive or invalid equity check
        if not math.isfinite(self.current_equity_usd) or self.current_equity_usd <= 0.0:
            if not is_risk_reducing:
                return RiskDecision(
                    approved=False,
                    violation_code=RiskViolationCode.MAX_DRAWDOWN_EXCEEDED,
                    reason=f"Current portfolio equity (${self.current_equity_usd:,.2f}) is non-positive or invalid.",
                )

        # In-flight orders aggregation
        in_flight_symbol_delta = sum(
            (1.0 if o.side.upper() == "BUY" else -1.0) * o.quantity
            for o_id, o in self.in_flight_orders.items()
            if o.symbol == order.symbol and o_id != order.order_id
        )
        effective_curr_qty = curr_qty + in_flight_symbol_delta
        effective_new_qty = effective_curr_qty + delta_qty

        # 4. Burst Rate Limiter
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

        # 6. Single Asset Concentration Cap (including in-flight orders)
        new_asset_notional = abs(effective_new_qty * order.price)
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

        # 7. Gross Leverage Ceiling (including in-flight orders)
        simulated_positions = dict(self.positions)
        simulated_positions[order.symbol] = effective_new_qty
        simulated_prices = dict(self.mark_prices)
        simulated_prices[order.symbol] = order.price

        simulated_gross = 0.0
        for s, q in simulated_positions.items():
            p = simulated_prices.get(s, order.price if s == order.symbol else 0.0)
            simulated_gross += abs(q * p)

        # Add all in-flight orders for other symbols
        for o_id, o in self.in_flight_orders.items():
            if o_id != order.order_id and o.symbol != order.symbol:
                p_inflight = simulated_prices.get(o.symbol, o.price)
                simulated_gross += abs(o.quantity * p_inflight)

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
        do_auto = self.auto_register_in_flight if auto_register_in_flight is None else auto_register_in_flight
        if do_auto:
            self.register_in_flight(order)

        return RiskDecision(
            approved=True,
            violation_code=RiskViolationCode.NONE,
            reason="Approved by Deterministic Risk Engine",
            metrics={"drawdown_pct": dd, "is_risk_reducing": is_risk_reducing},
        )
