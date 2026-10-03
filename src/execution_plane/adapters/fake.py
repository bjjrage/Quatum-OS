"""MOCK / TEST ONLY deterministic exchange. Never registered as a production venue."""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional

from src.execution_plane.adapters.base import (AdapterError, ExchangeAdapter, InvalidOrder,
                                               UnknownOutcomeError, VenueUnavailable)
from src.execution_plane.models import AccountSnapshot, FailureClass, InstrumentMeta, OrderIntent
from src.execution_plane.telemetry import RateLimited


class FakeExchangeAdapter(ExchangeAdapter):
    venue = "fake_venue"
    environment = "MOCK"
    is_test_only = True

    def __init__(self, venue: str = "fake_venue", now_ms=lambda: 1_700_000_000_000):
        self.venue = venue
        self._now_ms = now_ms
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.venue_fills: List[Dict[str, Any]] = []
        self.position_override: Dict[str, float] = {}
        self.submit_calls: List[Dict[str, Any]] = []
        self.cancel_calls: List[str] = []
        self.query_calls: List[str] = []
        self.clock_offset_ms = 0
        self.connected = False
        self.equity = 2000.0
        self.available = 2000.0
        self.query_fails = False
        self._submit_script: List[str] = []
        self._cancel_script: List[str] = []
        self._ids = itertools.count(1)
        self._trade_ids = itertools.count(1)
        self.stream_events: List[Dict[str, Any]] = []

    # ---- scenario scripting ----
    def script_submit(self, *behaviors: str) -> "FakeExchangeAdapter":
        self._submit_script.extend(behaviors)
        return self

    def script_cancel(self, *behaviors: str) -> "FakeExchangeAdapter":
        self._cancel_script.extend(behaviors)
        return self

    def venue_fill(self, client_order_id: str, qty: float, price: float) -> Dict[str, Any]:
        o = self.orders[client_order_id]
        qty = min(qty, o["qty"] - o["filled"])
        o["filled"] += qty
        o["status"] = "FILLED" if o["filled"] >= o["qty"] else "PARTIALLY_FILLED"
        f = {"venue_trade_id": f"T{next(self._trade_ids)}", "client_order_id": client_order_id,
             "venue_order_id": o["venue_order_id"], "symbol": o["symbol"], "side": o["side"], "price": price,
             "qty": qty, "fee": round(qty * price * 0.0004, 8), "fee_asset": "USDT", "is_taker": True,
             "timestamp_ns": self._now_ms() * 1_000_000}
        self.venue_fills.append(f)
        return f

    def corrupt_position(self, symbol: str, qty: float) -> None:
        self.position_override[symbol] = qty

    def add_orphan_order(self, client_order_id: str, symbol: str = "BTCUSDT", qty: float = 1.0) -> None:
        self.orders[client_order_id] = {"client_order_id": client_order_id, "venue_order_id": f"V{next(self._ids)}",
                                        "symbol": symbol, "side": "BUY", "qty": qty, "price": 1.0, "filled": 0.0,
                                        "status": "NEW"}

    # ---- contract ----
    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def health(self) -> Dict[str, Any]:
        return {"venue": self.venue, "status": "MOCK", "data_source": "MOCK", "test_only": True,
                "connected": self.connected}

    def capabilities(self) -> Dict[str, Any]:
        return {"venue": self.venue, "credentials": "NOT_APPLICABLE", "public_market_data": False,
                "account_read": True, "order_submit": True, "order_cancel": True, "private_stream": True,
                "sandbox_available": False, "live_available": False, "atomic_replace": False,
                "execution_mode": "LIVE_LOCKED", "data_source": "MOCK", "test_only": True}

    def get_server_time(self) -> int:
        return self._now_ms() + self.clock_offset_ms

    def _guard_query(self):
        if self.query_fails:
            raise VenueUnavailable("fake query failure", pre_send=False)

    def get_account(self) -> AccountSnapshot:
        self._guard_query()
        return AccountSnapshot(venue=self.venue, account_id="FAKE-ACCT", equity=self.equity,
                               available_balance=self.available, margin_used=self.equity - self.available,
                               positions=self.get_positions(), open_orders=self.get_open_orders(),
                               timestamp_ns=self._now_ms() * 1_000_000, data_source="MOCK", status="KNOWN")

    def get_balances(self) -> Dict[str, Any]:
        self._guard_query()
        return {"USDT": {"total": self.equity, "available": self.available}}

    def get_positions(self) -> List[Dict[str, Any]]:
        self._guard_query()
        pos: Dict[str, float] = {}
        for f in self.venue_fills:
            sgn = 1.0 if f.get("side", "BUY") == "BUY" else -1.0
            pos[f["symbol"]] = pos.get(f["symbol"], 0.0) + sgn * f["qty"]
        pos.update(self.position_override)
        return [{"symbol": s, "quantity": q, "entry_price": None} for s, q in sorted(pos.items()) if q != 0]

    def get_open_orders(self) -> List[Dict[str, Any]]:
        self._guard_query()
        return [dict(o) for o in self.orders.values() if o["status"] in ("NEW", "PARTIALLY_FILLED")]

    def get_order(self, client_order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        self.query_calls.append(client_order_id)
        self._guard_query()
        o = self.orders.get(client_order_id)
        return dict(o) if o else None

    def get_fills(self, symbol: Optional[str] = None, since_ns: Optional[int] = None) -> List[Dict[str, Any]]:
        self._guard_query()
        return [dict(f) for f in self.venue_fills if symbol in (None, f["symbol"])]

    def serialize_order(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        return {"venue": self.venue, "symbol": meta.venue_symbol, "side": intent.side, "type": intent.order_type,
                "qty": intent.quantity, "price": intent.limit_price, "client_order_id": intent.client_order_id,
                "tif": intent.time_in_force, "reduce_only": intent.reduce_only, "post_only": intent.post_only}

    def _accept(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        o = {"client_order_id": intent.client_order_id, "venue_order_id": f"V{next(self._ids)}",
             "symbol": intent.symbol, "side": intent.side, "qty": intent.quantity,
             "price": intent.limit_price or intent.reference_price or 1.0, "filled": 0.0, "status": "NEW"}
        self.orders[intent.client_order_id] = o
        return o

    def submit_order(self, permit, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        self._check_permit(permit, "SUBMIT", intent.client_order_id)
        beh = self._submit_script.pop(0) if self._submit_script else "ACK"
        self.submit_calls.append({"client_order_id": intent.client_order_id, "behavior": beh})
        if beh == "REJECT":
            raise InvalidOrder("fake venue rejected order", code="FAKE_REJECT")
        if beh == "RATE_LIMIT":
            raise RateLimited(0.0, "fake 429")
        if beh == "DISCONNECT":
            raise VenueUnavailable("fake disconnect before send", pre_send=True)
        if beh == "DISCONNECT_AFTER":
            self._accept(intent, meta)
            raise VenueUnavailable("fake disconnect after send", pre_send=False)
        if beh == "TIMEOUT_LOST":
            raise UnknownOutcomeError("fake timeout (order never reached venue)")
        o = self._accept(intent, meta)
        if beh == "TIMEOUT_ACCEPTED":
            raise UnknownOutcomeError("fake timeout (order accepted by venue)")
        fills = []
        if beh == "PARTIAL":
            fills.append(self.venue_fill(intent.client_order_id, intent.quantity * 0.4, o["price"]))
        elif beh == "FILL":
            fills.append(self.venue_fill(intent.client_order_id, intent.quantity, o["price"]))
        return {"venue_order_id": o["venue_order_id"], "status": o["status"], "fills": fills}

    def cancel_order(self, permit, client_order_id: str, symbol: str) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL", client_order_id)
        self.cancel_calls.append(client_order_id)
        beh = self._cancel_script.pop(0) if self._cancel_script else "OK"
        o = self.orders.get(client_order_id)
        if o is None:
            raise InvalidOrder("unknown order", code="UNKNOWN_ORDER")
        if beh == "REJECT":
            raise InvalidOrder("fake cancel rejected", code="CANCEL_REJECTED")
        if beh == "FILL_DURING_CANCEL":
            rem = o["qty"] - o["filled"]
            f = self.venue_fill(client_order_id, rem, o["price"])
            return {"status": "FILLED", "fills": [f]}
        if o["status"] == "FILLED" or beh == "ALREADY_FILLED":
            raise InvalidOrder("order already filled", code="ALREADY_FILLED")
        o["status"] = "CANCELED"
        return {"status": "CANCELED", "fills": []}

    def cancel_all(self, permit, symbol: Optional[str] = None) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL_ALL")
        n = 0
        for o in self.orders.values():
            if o["status"] in ("NEW", "PARTIALLY_FILLED") and symbol in (None, o["symbol"]):
                o["status"] = "CANCELED"
                n += 1
        return {"canceled": n}

    def normalize_private_event(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [raw]


class FakeStreamConnector:
    """Scriptable private-stream connector for tests."""

    def __init__(self, fail_first: int = 0, events: Optional[List[Dict[str, Any]]] = None):
        self.fail_first = fail_first
        self.attempts = 0
        self.events = list(events or [])
        self.open = False

    def connect(self) -> None:
        self.attempts += 1
        if self.attempts <= self.fail_first:
            raise ConnectionError("fake stream connect failure")
        self.open = True

    def close(self) -> None:
        self.open = False

    def poll(self) -> List[Dict[str, Any]]:
        ev, self.events = self.events, []
        return ev
