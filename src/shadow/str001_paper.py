"""STR-001 paper loop: shadow decisions -> ExecutionRouter (risk + signed permit) -> PaperBroker.

Everything goes through the router, so the Risk Engine is evaluated and the permit (bound to
symbol, side, quantity and price) is minted by the router only. Fills are walked against the
real executable quote captured in the shadow record, never against a mid price.

Binary contracts: a BUY_NO is modelled as buying a synthetic "<yes_token>:NO" contract priced at
1 - yes_bid with a book mirrored from the YES book. Positions are cash-settled at 0/1 on resolution.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.models import ExecFill, ExecutionMode, InstrumentMeta, OrderIntent, OrderState
from src.execution_plane.router import ExecutionRouter, InstrumentRegistry
from src.execution_plane.security import CredentialProvider
from src.execution_plane.store import ExecutionStore
from src.paper.broker import PaperBroker
from src.persistence.backend import LocalPersistenceBackend
from src.risk.engine import DeterministicRiskEngine, RiskLimits

VENUE = "polymarket"
STRATEGY_ID = "STR-001"


class Str001PaperTrader:
    def __init__(self, out_dir: Path = Path("data/paper"), initial_cash_usd: float = 10_000.0,
                 notional_per_trade_usd: float = 50.0, max_open_positions: int = 20,
                 max_open_per_underlying: int = 5, fee_bps: float = 0.0, slippage_bps: float = 0.0,
                 latency_ms: float = 300.0, clock_ns: Callable[[], int] = time.time_ns,
                 limits: Optional[RiskLimits] = None):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.clock_ns = clock_ns
        self.notional = notional_per_trade_usd
        self.max_open, self.max_per_und = max_open_positions, max_open_per_underlying
        self.broker = PaperBroker(initial_cash_usd=initial_cash_usd, simulated_latency_ms=latency_ms,
                                  maker_fee_bps=0.0, taker_fee_bps=fee_bps, base_slippage_bps=slippage_bps)
        self.risk = DeterministicRiskEngine(
            initial_equity_usd=initial_cash_usd,
            limits=limits or RiskLimits(live_capital_locked=True, max_orders_per_window=1000))
        self.backend = LocalPersistenceBackend(self.out_dir / "paper_control_plane.db")
        self.store = ExecutionStore(self.backend)
        self.router = ExecutionRouter(
            self.store, self.risk, {}, InstrumentRegistry(), mode=ExecutionMode.PAPER,
            paper_broker=self.broker, credentials=CredentialProvider({}), clock_ns=clock_ns)
        self.open: Dict[str, Dict[str, Any]] = {}   # market_id -> {symbol, underlying, yes_token, side}
        self.n = 0

    def _log(self, name: str, rec: Dict[str, Any]) -> None:
        with open(self.out_dir / f"{name}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    def _book(self, rec: Dict[str, Any], buy_no: bool) -> Dict[str, float]:
        q = rec["quote"]
        if buy_no:  # mirrored NO book
            return {"best_bid": 1.0 - q["ask"], "best_ask": 1.0 - q["bid"],
                    "bid_size": q["ask_size"], "ask_size": q["bid_size"]}
        return {"best_bid": q["bid"], "best_ask": q["ask"], "bid_size": q["bid_size"], "ask_size": q["ask_size"]}

    def on_decision(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle one shadow record. Returns an execution log entry (or None if nothing to do)."""
        if rec.get("status") != "PRICED" or rec.get("action") not in ("BUY_YES", "BUY_NO"):
            return None
        mid = rec["market_id"]
        if mid in self.open:
            return None
        if len(self.open) >= self.max_open:
            return self._skip(rec, "MAX_OPEN_POSITIONS")
        if sum(1 for p in self.open.values() if p["underlying"] == rec["underlying"]) >= self.max_per_und:
            return self._skip(rec, "MAX_PER_UNDERLYING")
        buy_no = rec["action"] == "BUY_NO"
        symbol = rec["yes_token_id"] + (":NO" if buy_no else "")
        price = round(float(rec["entry_price"]), 4)
        qty = round(self.notional / price, 2)
        if qty <= 0:
            return self._skip(rec, "ZERO_QTY")
        self.n += 1
        now = self.clock_ns()
        quote_ts = rec["quote"].get("ts_ns") or now
        intent = OrderIntent(
            intent_id=f"str001-{mid}-{self.n}", strategy_id=STRATEGY_ID, strategy_version="shadow-1",
            capital_pocket_id="paper-pocket", venue=VENUE, symbol=symbol, side="BUY", order_type="LIMIT",
            quantity=qty, limit_price=price, market_data_timestamp_ns=min(int(quote_ts), now),
            decision_timestamp_ns=now, max_signal_age_ms=120_000.0, created_at_ns=now,
            client_order_id=f"co-{mid}-{self.n}", idempotency_key=f"idem-{mid}-{rec['ts_utc']}")
        order = self.router.submit(intent)
        entry = {"ts_utc": rec["ts_utc"], "market_id": mid, "symbol": symbol, "qty": qty, "limit": price,
                 "state": order.state.value, "reason": order.reason}
        if order.state in (OrderState.REJECTED, OrderState.RISK_REJECTED):
            self._log("paper_orders", entry)
            return entry
        book = self._book(rec, buy_no)
        po = self.broker.orders.get(order.venue_order_id)
        self.broker.on_market_event(symbol=symbol, best_bid=book["best_bid"], best_ask=book["best_ask"],
                                    event_time_ns=now + self.broker.latency_ns,
                                    bid_size=book["bid_size"], ask_size=book["ask_size"])
        if po is not None and po.filled_qty > 0 and not order.terminal:
            self.router.apply_fill(order, ExecFill(
                fill_id=f"paper:{po.order_id}", intent_id=intent.intent_id, client_order_id=intent.client_order_id,
                venue=VENUE, venue_order_id=po.order_id, venue_trade_id=f"paper:{po.order_id}",
                price=po.filled_price or price, quantity=po.filled_qty, fee=po.fee_paid or 0.0,
                is_taker=po.is_taker, timestamp_ns=now + self.broker.latency_ns))
            if order.terminal and hasattr(self.risk, "release_in_flight"):
                self.risk.release_in_flight(intent.client_order_id)
        pos = self.broker.positions.get(symbol)
        if pos is not None and pos.quantity != 0:
            self.open[mid] = {"symbol": symbol, "underlying": rec["underlying"], "side": rec["action"],
                              "entry": pos.average_entry_price, "qty": pos.quantity}
        entry.update({"state": order.state.value, "filled_qty": getattr(po, "filled_qty", 0.0),
                      "filled_price": getattr(po, "filled_price", None)})
        self._log("paper_orders", entry)
        self._sync_risk()
        return entry

    def _skip(self, rec: Dict[str, Any], why: str) -> Dict[str, Any]:
        e = {"ts_utc": rec["ts_utc"], "market_id": rec["market_id"], "state": "SKIPPED", "reason": why}
        self._log("paper_orders", e)
        return e

    def settle(self, market_id: str, yes_outcome: int) -> Optional[float]:
        p = self.open.pop(market_id, None)
        if p is None:
            return None
        payout = float(yes_outcome) if not p["symbol"].endswith(":NO") else float(1 - yes_outcome)
        pnl = self.broker.settle_position(p["symbol"], payout)
        self._log("paper_settlements", {"market_id": market_id, "symbol": p["symbol"], "payout": payout,
                                        "pnl_usd": pnl, "cash_usd": self.broker.cash_usd})
        self._sync_risk()
        return pnl

    def _sync_risk(self) -> None:
        marks = {p["symbol"]: p["entry"] for p in self.open.values()}
        try:
            s = self.broker.get_portfolio_summary(marks)
            self.risk.update_portfolio_state(equity_usd=float(s["total_equity_usd"]),
                                             positions={p["symbol"]: p["qty"] for p in self.open.values()},
                                             mark_prices=marks)
        except Exception as ex:  # reporting must not hide an execution outcome
            self._log("errors", {"where": "sync_risk", "error": repr(ex)})

    def summary(self) -> Dict[str, Any]:
        realized = sum(p.realized_pnl_usd for p in self.broker.positions.values())
        return {"cash_usd": self.broker.cash_usd, "open_positions": len(self.open), "realized_pnl_usd": realized,
                "fees_usd": sum(p.fees_paid_usd for p in self.broker.positions.values())}
