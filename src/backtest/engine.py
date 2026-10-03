"""Deterministic event-driven backtesting engine with realistic fill and fee simulation."""
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Any, List, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class SimulatedOrder:
    order_id: str
    symbol: str
    venue: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    created_at_ns: int = 0
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_at_ns: Optional[int] = None
    fee_paid: float = 0.0


@dataclass
class SimulatedTrade:
    trade_id: str
    order_id: str
    symbol: str
    venue: str
    side: OrderSide
    price: float
    quantity: float
    fee_paid: float
    ts_ns: int


class DeterministicBacktestEngine:
    """Event-driven, deterministic market simulator and portfolio ledger."""

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        maker_fee_bps: float = 1.0,
        taker_fee_bps: float = 4.0,
        slippage_bps: float = 1.0,
        fill_latency_ns: int = 10_000_000,  # 10ms execution delay
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps
        self.fill_latency_ns = fill_latency_ns

        # Portfolio state
        self.positions: Dict[str, float] = {}  # symbol -> net quantity (can be negative for short)
        self.entry_prices: Dict[str, float] = {}
        self.last_prices: Dict[str, float] = {}

        self.pending_orders: List[SimulatedOrder] = []
        self.trades: List[SimulatedTrade] = []
        self.equity_history: List[float] = [initial_cash]
        self.timestamps_ns: List[int] = []

        self._trade_counter = 0

    @property
    def total_equity(self) -> float:
        """Total portfolio equity = cash + unrealized value of all positions."""
        unrealized = 0.0
        for sym, qty in self.positions.items():
            if abs(qty) > 1e-9:
                curr_price = self.last_prices.get(sym, self.entry_prices.get(sym, 0.0))
                # For long: qty * curr_price
                # For short: qty is negative, entry price was received, mark-to-market is qty * (curr_price - entry_price)
                unrealized += qty * curr_price
        return self.cash + unrealized

    def submit_order(
        self,
        symbol: str,
        venue: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        limit_price: Optional[float] = None,
        current_ts_ns: int = 0,
    ) -> SimulatedOrder:
        """Submit an order to the matching book."""
        self._trade_counter += 1
        order = SimulatedOrder(
            order_id=f"ord_{self._trade_counter:06d}",
            symbol=symbol,
            venue=venue,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            created_at_ns=current_ts_ns,
            status=OrderStatus.PENDING,
        )
        self.pending_orders.append(order)
        return order

    def on_market_tick(
        self,
        symbol: str,
        bid_price: float,
        ask_price: float,
        current_ts_ns: int,
    ) -> List[SimulatedTrade]:
        """Process incoming market tick, updating marks and executing eligible pending orders."""
        mid_price = (bid_price + ask_price) / 2.0
        self.last_prices[symbol] = mid_price

        executed_trades: List[SimulatedTrade] = []
        remaining_orders: List[SimulatedOrder] = []

        for order in self.pending_orders:
            if order.symbol != symbol:
                remaining_orders.append(order)
                continue

            # Respect execution latency
            if current_ts_ns - order.created_at_ns < self.fill_latency_ns:
                remaining_orders.append(order)
                continue

            fill_price: Optional[float] = None
            is_taker = False

            if order.order_type == OrderType.MARKET:
                is_taker = True
                slippage_mult = (self.slippage_bps * 1e-4)
                if order.side == OrderSide.BUY:
                    fill_price = ask_price * (1.0 + slippage_mult)
                else:
                    fill_price = bid_price * (1.0 - slippage_mult)

            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and ask_price <= order.limit_price:
                    fill_price = order.limit_price
                    is_taker = False
                elif order.side == OrderSide.SELL and bid_price >= order.limit_price:
                    fill_price = order.limit_price
                    is_taker = False

            if fill_price is not None:
                # Calculate fee
                fee_rate = (self.taker_fee_bps if is_taker else self.maker_fee_bps) * 1e-4
                trade_notional = fill_price * order.quantity
                fee = trade_notional * fee_rate

                order.status = OrderStatus.FILLED
                order.filled_price = fill_price
                order.filled_at_ns = current_ts_ns
                order.fee_paid = fee

                # Update portfolio cash and inventory
                if order.side == OrderSide.BUY:
                    self.cash -= (trade_notional + fee)
                    prev_qty = self.positions.get(symbol, 0.0)
                    new_qty = prev_qty + order.quantity
                    self.positions[symbol] = new_qty
                    if new_qty > 0:
                        self.entry_prices[symbol] = fill_price
                else:
                    self.cash += (trade_notional - fee)
                    prev_qty = self.positions.get(symbol, 0.0)
                    new_qty = prev_qty - order.quantity
                    self.positions[symbol] = new_qty
                    if new_qty < 0:
                        self.entry_prices[symbol] = fill_price

                trade = SimulatedTrade(
                    trade_id=f"trd_{self._trade_counter}_{len(self.trades)+1}",
                    order_id=order.order_id,
                    symbol=symbol,
                    venue=order.venue,
                    side=order.side,
                    price=fill_price,
                    quantity=order.quantity,
                    fee_paid=fee,
                    ts_ns=current_ts_ns,
                )
                self.trades.append(trade)
                executed_trades.append(trade)
            else:
                remaining_orders.append(order)

        self.pending_orders = remaining_orders
        self.equity_history.append(self.total_equity)
        self.timestamps_ns.append(current_ts_ns)

        return executed_trades
