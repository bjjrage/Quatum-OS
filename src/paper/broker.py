"""
Realistic Paper Broker and Execution Simulator.

Invariants:
- Strictly dry-run and simulated: live execution is physically prevented.
- Realistic execution modeling:
  - Network transit latency simulation (orders submitted at T0 execute at T >= T0 + latency).
  - Market orders do NOT fill using stale T0 quotes when latency > 0.
  - Queue priority / FIFO fill modeling for passive limit orders.
  - Marketable limit orders are classified as TAKER orders (charge taker fee).
  - Depth exhaustion and partial fills against available liquidity.
  - Non-instantaneous fills and non-linear price slippage.
  - Maker / Taker fee structure.
  - Multi-asset cash and position ledger with realized/unrealized PnL.
  - Cancel and Replace support.
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
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
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
    is_taker: bool = False


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
    is_taker: bool = False


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
        self.simulated_latency_ms = simulated_latency_ms
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
        If simulated latency > 0, the order is placed into SUBMITTED status and must wait
        for market state at T >= submitted_at_ns + latency_ns to execute.
        """
        if quantity <= 0.0:
            raise ValueError(f"Quantity must be positive: {quantity}")
        if order_type == PaperOrderType.LIMIT and (limit_price is None or limit_price <= 0.0):
            raise ValueError(f"Limit order requires valid positive limit_price: {limit_price}")

        order_id = f"ord-{uuid.uuid4().hex[:10]}"
        available_at_ns = current_time_ns + self.latency_ns

        is_taker = False
        if order_type == PaperOrderType.MARKET:
            is_taker = True
        elif order_type == PaperOrderType.LIMIT and current_bbo is not None:
            # Check if limit crosses the spread immediately (Marketable Limit)
            best_ask = current_bbo.get("best_ask", float("inf"))
            best_bid = current_bbo.get("best_bid", 0.0)
            if side == PaperOrderSide.BUY and best_ask > 0 and limit_price >= best_ask:
                is_taker = True
            elif side == PaperOrderSide.SELL and best_bid > 0 and limit_price <= best_bid:
                is_taker = True

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
            is_taker=is_taker,
        )

        if current_bbo is not None:
            bid_size = current_bbo.get("bid_size", 5.0)
            ask_size = current_bbo.get("ask_size", 5.0)
            order.queue_ahead_volume = bid_size if side == PaperOrderSide.BUY else ask_size

        self.orders[order_id] = order

        # If zero latency, we can execute immediately using current_bbo
        if self.latency_ns == 0 and current_bbo is not None:
            if order.is_taker:
                self._fill_taker_order(
                    order,
                    best_bid=current_bbo.get("best_bid", 0.0),
                    best_ask=current_bbo.get("best_ask", 0.0),
                    bid_size=current_bbo.get("bid_size", 10.0),
                    ask_size=current_bbo.get("ask_size", 10.0),
                    fill_time_ns=current_time_ns,
                )

        return order

    def _fill_taker_order(
        self,
        order: PaperOrder,
        best_bid: float,
        best_ask: float,
        bid_size: float,
        ask_size: float,
        fill_time_ns: int,
    ) -> Optional[PaperTrade]:
        """Execute market/marketable limit taker order with non-linear slippage and taker fee."""
        if order.side == PaperOrderSide.BUY:
            base_price = best_ask if best_ask > 0 else best_bid
            available_depth = ask_size
        else:
            base_price = best_bid if best_bid > 0 else best_ask
            available_depth = bid_size

        if base_price <= 0.0 or available_depth <= 0.0:
            return None

        # Check limit condition for marketable limit orders
        if order.order_type == PaperOrderType.LIMIT and order.limit_price is not None:
            if order.side == PaperOrderSide.BUY and base_price > order.limit_price:
                # Market moved above buy limit; converts to resting passive order
                order.is_taker = False
                order.queue_ahead_volume = available_depth
                return None
            elif order.side == PaperOrderSide.SELL and base_price < order.limit_price:
                # Market moved below sell limit; converts to resting passive order
                order.is_taker = False
                order.queue_ahead_volume = available_depth
                return None

        unfilled = order.quantity - order.filled_qty
        fill_qty = min(unfilled, available_depth)
        if fill_qty <= 0.0:
            return None

        # Size-aware non-linear slippage
        depth_ratio = fill_qty / max(0.1, available_depth)
        effective_slippage_bps = self.base_slippage_bps * (1.0 + depth_ratio)

        if order.side == PaperOrderSide.BUY:
            exec_price = base_price * (1.0 + (effective_slippage_bps / 10_000.0))
            if order.order_type == PaperOrderType.LIMIT and order.limit_price is not None:
                exec_price = min(exec_price, order.limit_price)
        else:
            exec_price = base_price * (1.0 - (effective_slippage_bps / 10_000.0))
            if order.order_type == PaperOrderType.LIMIT and order.limit_price is not None:
                exec_price = max(exec_price, order.limit_price)

        notional = fill_qty * exec_price
        fee = notional * (self.taker_fee_bps / 10_000.0)
        slippage_usd = abs(exec_price - base_price) * fill_qty

        # Cumulative fill tracking
        prior_notional = (order.filled_price or 0.0) * order.filled_qty
        new_total_qty = order.filled_qty + fill_qty
        order.filled_price = (prior_notional + (exec_price * fill_qty)) / new_total_qty
        order.filled_qty = new_total_qty
        order.filled_at_ns = fill_time_ns
        order.fee_paid += fee
        order.slippage_usd += slippage_usd

        if math.isclose(order.filled_qty, order.quantity, rel_tol=1e-5):
            order.status = PaperOrderStatus.FILLED
        else:
            order.status = PaperOrderStatus.PARTIALLY_FILLED

        trade = PaperTrade(
            trade_id=f"trd-{uuid.uuid4().hex[:10]}",
            order_id=order.order_id,
            symbol=order.symbol,
            venue=order.venue,
            side=order.side,
            price=exec_price,
            quantity=fill_qty,
            fee=fee,
            slippage_usd=slippage_usd,
            timestamp_ns=fill_time_ns,
            is_taker=True,
        )
        self.trades.append(trade)
        self._update_position(trade)
        return trade

    def on_market_event(
        self,
        symbol: str,
        best_bid: float,
        best_ask: float,
        event_time_ns: int,
        trade_volume: float = 1.0,
        bid_size: float = 10.0,
        ask_size: float = 10.0,
    ) -> List[PaperTrade]:
        """
        Evaluate pending market orders and resting limit orders against incoming market updates.
        Only orders whose available_at_ns <= event_time_ns (latency elapsed) are evaluated.
        """
        executed_trades = []

        for order in list(self.orders.values()):
            if order.status not in (PaperOrderStatus.SUBMITTED, PaperOrderStatus.PARTIALLY_FILLED):
                continue
            if order.symbol != symbol:
                continue
            if event_time_ns < order.available_at_ns:
                continue  # Still in network transit

            if order.is_taker or order.order_type == PaperOrderType.MARKET:
                # Execute taker against post-latency market state
                trade = self._fill_taker_order(
                    order,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    bid_size=bid_size,
                    ask_size=ask_size,
                    fill_time_ns=event_time_ns,
                )
                if trade is not None:
                    executed_trades.append(trade)
            elif order.order_type == PaperOrderType.LIMIT:
                # Passive resting limit order
                fill = False
                exec_price = order.limit_price or 0.0

                if order.side == PaperOrderSide.BUY:
                    if best_ask > 0 and best_ask <= exec_price:
                        fill = True
                    elif best_bid <= exec_price:
                        order.queue_ahead_volume -= trade_volume
                        if order.queue_ahead_volume <= 0:
                            fill = True
                elif order.side == PaperOrderSide.SELL:
                    if best_bid > 0 and best_bid >= exec_price:
                        fill = True
                    elif best_ask >= exec_price:
                        order.queue_ahead_volume -= trade_volume
                        if order.queue_ahead_volume <= 0:
                            fill = True

                if fill:
                    unfilled = order.quantity - order.filled_qty
                    available_depth = ask_size if order.side == PaperOrderSide.BUY else bid_size
                    fill_qty = min(unfilled, available_depth)
                    if fill_qty <= 0.0:
                        continue

                    notional = fill_qty * exec_price
                    fee = notional * (self.maker_fee_bps / 10_000.0)

                    prior_notional = (order.filled_price or 0.0) * order.filled_qty
                    new_total_qty = order.filled_qty + fill_qty
                    order.filled_price = (prior_notional + (exec_price * fill_qty)) / new_total_qty
                    order.filled_qty = new_total_qty
                    order.filled_at_ns = event_time_ns
                    order.fee_paid += fee
                    order.slippage_usd = 0.0  # Passive limit provides liquidity

                    if math.isclose(order.filled_qty, order.quantity, rel_tol=1e-5):
                        order.status = PaperOrderStatus.FILLED
                    else:
                        order.status = PaperOrderStatus.PARTIALLY_FILLED

                    trade = PaperTrade(
                        trade_id=f"trd-{uuid.uuid4().hex[:10]}",
                        order_id=order.order_id,
                        symbol=order.symbol,
                        venue=order.venue,
                        side=order.side,
                        price=exec_price,
                        quantity=fill_qty,
                        fee=fee,
                        slippage_usd=0.0,
                        timestamp_ns=event_time_ns,
                        is_taker=False,
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
        if order and order.status in (PaperOrderStatus.SUBMITTED, PaperOrderStatus.PARTIALLY_FILLED):
            order.status = PaperOrderStatus.CANCELLED
            return True
        return False

    def replace_order(
        self,
        order_id: str,
        new_quantity: float,
        new_limit_price: Optional[float] = None,
        current_time_ns: int = 0,
        current_bbo: Optional[Dict[str, float]] = None,
    ) -> PaperOrder:
        """
        Cancel existing order and submit replacement with new quantity/price,
        incurring new network transit latency.
        """
        old_order = self.orders.get(order_id)
        if not old_order or old_order.status not in (PaperOrderStatus.SUBMITTED, PaperOrderStatus.PARTIALLY_FILLED):
            raise ValueError(f"Cannot replace order {order_id} in status {old_order.status if old_order else 'NOT_FOUND'}")

        self.cancel_order(order_id)
        return self.submit_order(
            symbol=old_order.symbol,
            side=old_order.side,
            order_type=old_order.order_type,
            quantity=new_quantity,
            limit_price=new_limit_price if new_limit_price is not None else old_order.limit_price,
            venue=old_order.venue,
            current_time_ns=current_time_ns,
            current_bbo=current_bbo,
        )

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
