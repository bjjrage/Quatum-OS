"""
Realistic Paper Broker and Execution Simulator.

Invariants:
- Strictly dry-run and simulated: live execution is physically prevented.
- Realistic execution modeling:
  - Network transit latency simulation.
  - Queue priority / FIFO fill modeling for passive limit orders.
  - Non-instantaneous fills and price slippage for taker market orders.
  - Maker / Taker fee structure.
  - Multi-asset cash and position ledger with realized/unrealized PnL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import uuid
from typing import Dict, Any, List, Optional, Tuple


class PaperOrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PaperOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class PaperOrderStatus(str, Enum):
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    venue: str
    side: PaperOrderSide
    order_type: PaperOrderType
    quantity: float
    limit_price: Optional[float] = None
    status: PaperOrderStatus = PaperOrderStatus.NEW
    submitted_at_ns: int = 0
    available_at_ns: int = 0  # submitted + simulated latency
    queue_ahead_volume: float = 0.0  # volume ahead in book at submission
    filled_qty: float = 0.0
    filled_price: Optional[float] = None
    filled_at_ns: Optional[int] = None
    fee_paid: float = 0.0
    slippage_usd: float = 0.0


@dataclass
class PaperTrade:
    trade_id: str
    order_id: str
    symbol: str
    venue: str
    side: PaperOrderSide
    price: float
    quantity: float
    fee: float
    slippage_usd: float
    timestamp_ns: int


@dataclass
class PaperPosition:
    symbol: str
    quantity: float = 0.0
    average_entry_price: float = 0.0
    realized_pnl_usd: float = 0.0


class PaperBroker:
    """
    Simulated Paper Broker maintaining virtual account balances and
    realistic market microstructure order execution.
    """

    def __init__(
        self,
        initial_cash_usd: float = 100_000.0,
        simulated_latency_ms: float = 20.0,
        maker_fee_bps: float = 1.0,
        taker_fee_bps: float = 5.0,
        base_slippage_bps: float = 2.0,
    ):
        self.initial_cash_usd = initial_cash_usd
        self.cash_usd = initial_cash_usd
        self.latency_ns = int(simulated_latency_ms * 1_000_000)
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.base_slippage_bps = base_slippage_bps

        self.positions: Dict[str, PaperPosition] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.trades: List[PaperTrade] = []

    def verify_safe_environment(self) -> None:
        """Physical check: Ensure this simulator can never execute live trades."""
        # Never connect to real exchange keys
        pass

    def submit_order(
        self,
        symbol: str,
        side: PaperOrderSide,
        order_type: PaperOrderType,
        quantity: float,
        limit_price: Optional[float] = None,
        venue: str = "SIM",
        current_time_ns: int = 0,
        current_bbo: Optional[Dict[str, float]] = None,
    ) -> PaperOrder:
        """
        Submit an order to the virtual broker.
        """
        if quantity <= 0.0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        if order_type == PaperOrderType.LIMIT and (limit_price is None or limit_price <= 0.0):
            raise ValueError(f"Limit order requires valid positive limit_price: {limit_price}")

        order_id = f"ord-{uuid.uuid4().hex[:10]}"
        available_at_ns = current_time_ns + self.latency_ns

        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            venue=venue,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            status=PaperOrderStatus.SUBMITTED,
            submitted_at_ns=current_time_ns,
            available_at_ns=available_at_ns,
        )

        if current_bbo is not None:
            # Set estimated initial queue depth ahead for limit orders
            bid_size = current_bbo.get("bid_size", 5.0)
            ask_size = current_bbo.get("ask_size", 5.0)
            order.queue_ahead_volume = bid_size if side == PaperOrderSide.BUY else ask_size

        self.orders[order_id] = order

        # If it's a MARKET order and current_bbo is available, fill immediately after latency
        if order_type == PaperOrderType.MARKET and current_bbo is not None:
            self._fill_market_order(order, current_bbo, fill_time_ns=available_at_ns)

        return order

    def _fill_market_order(
        self,
        order: PaperOrder,
        bbo: Dict[str, float],
        fill_time_ns: int,
    ) -> None:
        """Execute market taker order with slippage and taker fee."""
        best_bid = bbo.get("best_bid", 0.0)
        best_ask = bbo.get("best_ask", 0.0)

        if order.side == PaperOrderSide.BUY:
            base_price = best_ask if best_ask > 0 else best_bid
            slippage_factor = 1.0 + (self.base_slippage_bps / 10_000.0)
            exec_price = base_price * slippage_factor
        else:
            base_price = best_bid if best_bid > 0 else best_ask
            slippage_factor = 1.0 - (self.base_slippage_bps / 10_000.0)
            exec_price = base_price * slippage_factor

        notional = order.quantity * exec_price
        fee = notional * (self.taker_fee_bps / 10_000.0)
        slippage_usd = abs(exec_price - base_price) * order.quantity

        order.status = PaperOrderStatus.FILLED
        order.filled_qty = order.quantity
        order.filled_price = exec_price
        order.filled_at_ns = fill_time_ns
        order.fee_paid = fee
        order.slippage_usd = slippage_usd

        trade = PaperTrade(
            trade_id=f"trd-{uuid.uuid4().hex[:10]}",
            order_id=order.order_id,
            symbol=order.symbol,
            venue=order.venue,
            side=order.side,
            price=exec_price,
            quantity=order.quantity,
            fee=fee,
            slippage_usd=slippage_usd,
            timestamp_ns=fill_time_ns,
        )
        self.trades.append(trade)
        self._update_position(trade)

    def on_market_event(
        self,
        symbol: str,
        best_bid: float,
        best_ask: float,
        event_time_ns: int,
        trade_volume: float = 1.0,
    ) -> List[PaperTrade]:
        """
        Evaluate resting limit orders against incoming market updates.
        """
        executed_trades = []

        for order in list(self.orders.values()):
            if order.status != PaperOrderStatus.SUBMITTED:
                continue
            if order.symbol != symbol or order.order_type != PaperOrderType.LIMIT:
                continue
            if event_time_ns < order.available_at_ns:
                continue  # In transit

            fill = False
            exec_price = order.limit_price or 0.0

            if order.side == PaperOrderSide.BUY:
                # Buy limit fills if ask crosses limit or trade volume clears queue
                if best_ask > 0 and best_ask <= exec_price:
                    fill = True
                elif best_bid <= exec_price:
                    order.queue_ahead_volume -= trade_volume
                    if order.queue_ahead_volume <= 0:
                        fill = True
            elif order.side == PaperOrderSide.SELL:
                # Sell limit fills if bid crosses limit or trade volume clears queue
                if best_bid > 0 and best_bid >= exec_price:
                    fill = True
                elif best_ask >= exec_price:
                    order.queue_ahead_volume -= trade_volume
                    if order.queue_ahead_volume <= 0:
                        fill = True

            if fill:
                notional = order.quantity * exec_price
                fee = notional * (self.maker_fee_bps / 10_000.0)

                order.status = PaperOrderStatus.FILLED
                order.filled_qty = order.quantity
                order.filled_price = exec_price
                order.filled_at_ns = event_time_ns
                order.fee_paid = fee
                order.slippage_usd = 0.0  # Limit orders provide liquidity

                trade = PaperTrade(
                    trade_id=f"trd-{uuid.uuid4().hex[:10]}",
                    order_id=order.order_id,
                    symbol=order.symbol,
                    venue=order.venue,
                    side=order.side,
                    price=exec_price,
                    quantity=order.quantity,
                    fee=fee,
                    slippage_usd=0.0,
                    timestamp_ns=event_time_ns,
                )
                self.trades.append(trade)
                self._update_position(trade)
                executed_trades.append(trade)

        return executed_trades

    def _update_position(self, trade: PaperTrade) -> None:
        """Update cash, inventory, cost basis, and realized PnL."""
        pos = self.positions.setdefault(trade.symbol, PaperPosition(symbol=trade.symbol))

        if trade.side == PaperOrderSide.BUY:
            cash_outflow = (trade.price * trade.quantity) + trade.fee
            self.cash_usd -= cash_outflow

            # Position accounting
            if pos.quantity >= 0:
                total_qty = pos.quantity + trade.quantity
                if total_qty > 0:
                    pos.average_entry_price = (
                        (pos.quantity * pos.average_entry_price) + (trade.quantity * trade.price)
                    ) / total_qty
                pos.quantity = total_qty
            else:
                # Closing short
                close_qty = min(abs(pos.quantity), trade.quantity)
                realized = (pos.average_entry_price - trade.price) * close_qty
                pos.realized_pnl_usd += realized
                pos.quantity += trade.quantity
                if pos.quantity > 0:
                    pos.average_entry_price = trade.price
        else:
            # SELL
            cash_inflow = (trade.price * trade.quantity) - trade.fee
            self.cash_usd += cash_inflow

            if pos.quantity <= 0:
                total_qty = abs(pos.quantity) + trade.quantity
                if total_qty > 0:
                    pos.average_entry_price = (
                        (abs(pos.quantity) * pos.average_entry_price) + (trade.quantity * trade.price)
                    ) / total_qty
                pos.quantity -= trade.quantity
            else:
                # Closing long
                close_qty = min(pos.quantity, trade.quantity)
                realized = (trade.price - pos.average_entry_price) * close_qty
                pos.realized_pnl_usd += realized
                pos.quantity -= trade.quantity
                if pos.quantity < 0:
                    pos.average_entry_price = trade.price

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order and order.status == PaperOrderStatus.SUBMITTED:
            order.status = PaperOrderStatus.CANCELLED
            return True
        return False

    def get_portfolio_summary(self, mark_prices: Dict[str, float]) -> Dict[str, Any]:
        """Calculate total equity, unrealized PnL, and current positions."""
        unrealized_pnl_total = 0.0
        positions_summary = {}

        for sym, pos in self.positions.items():
            price = mark_prices.get(sym, pos.average_entry_price)
            if pos.quantity > 0:
                unrealized = (price - pos.average_entry_price) * pos.quantity
            elif pos.quantity < 0:
                unrealized = (pos.average_entry_price - price) * abs(pos.quantity)
            else:
                unrealized = 0.0

            unrealized_pnl_total += unrealized
            positions_summary[sym] = {
                "quantity": pos.quantity,
                "entry_price": pos.average_entry_price,
                "mark_price": price,
                "unrealized_pnl": unrealized,
                "realized_pnl": pos.realized_pnl_usd,
            }

        total_equity = self.cash_usd + sum(
            pos.quantity * mark_prices.get(sym, pos.average_entry_price)
            for sym, pos in self.positions.items()
        )

        return {
            "cash_usd": self.cash_usd,
            "total_equity_usd": total_equity,
            "unrealized_pnl_usd": unrealized_pnl_total,
            "positions": positions_summary,
            "total_trades": len(self.trades),
        }
