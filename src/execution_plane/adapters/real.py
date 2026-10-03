"""Real venue adapters (Binance USD-M, Bybit v5 derivatives, Deribit) behind an injectable Transport.

No network is performed unless a Transport is injected, and every mutating call requires a router-issued
SubmitPermit; LIVE-environment adapters additionally require LIVE mode + authorized capital > 0.
Venue-specific semantics (signing, serialization, normalization, error mapping) live ONLY here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.adapters.base import (AdapterError, AuthFailure, ExchangeAdapter, InvalidOrder,
                                               TransportNotConfigured, UnknownOutcomeError, VenueUnavailable)
from src.execution_plane.models import AccountSnapshot, FailureClass, InstrumentMeta, OrderIntent
from src.execution_plane.security import (CONFIGURED, CredentialProvider, CredentialsNotConfigured,
                                          redact_text)
from src.execution_plane.telemetry import RateLimited, VenueRateLimiter


@dataclass
class HttpResponse:
    status: int
    body: Any
    headers: Dict[str, str] = field(default_factory=dict)


class TransportTimeout(Exception):
    def __init__(self, sent: bool, message: str = "timeout"):
        super().__init__(message)
        self.sent = sent


class TransportConnectError(Exception):
    """Provably never transmitted."""


class UrllibTransport:
    """Stdlib HTTP transport. NOT used by default and never used in tests."""

    def request(self, method, url, headers=None, params=None, json_body=None, timeout_s=10.0) -> HttpResponse:
        if params:
            url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        data = json.dumps(json_body, separators=(",", ":")).encode() if json_body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}))
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return HttpResponse(r.status, json.loads(r.read() or b"null"), dict(r.headers))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read() or b"null")
            except Exception:
                body = None
            return HttpResponse(e.code, body, dict(e.headers or {}))
        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                raise TransportConnectError(str(e)) from e
            raise TransportTimeout(sent=True, message=str(e)) from e
        except TimeoutError as e:
            raise TransportTimeout(sent=True, message=str(e)) from e


def fnum(x: Any) -> str:
    """Exact decimal string, no exponent."""
    return format(Decimal(str(x)).normalize(), "f")


def _f(x: Any) -> Optional[float]:
    try:
        return None if x in (None, "") else float(x)
    except (TypeError, ValueError):
        return None


class RestAdapter(ExchangeAdapter):
    BASE: Dict[str, str] = {}
    PUBLIC_MD = "UNKNOWN"

    def __init__(self, credentials: Optional[CredentialProvider] = None, environment: str = "LIVE",
                 transport: Any = None, rate_limiter: Optional[VenueRateLimiter] = None,
                 now_ms: Callable[[], int] = lambda: int(time.time() * 1000)):
        if environment not in ("LIVE", "SANDBOX"):
            raise ValueError("environment must be LIVE or SANDBOX (explicit; no implicit fallback)")
        self.credentials = credentials or CredentialProvider()
        self.environment = environment
        self.transport = transport
        self.rate = rate_limiter or VenueRateLimiter(self.venue)
        self._now_ms = now_ms
        self.connected = False
        self.last_ok_ns: Optional[int] = None
        self.last_error: Optional[str] = None

    # ---- helpers ----
    @property
    def base_url(self) -> str:
        return self.BASE[self.environment]  # SANDBOX never falls back to LIVE URL

    def _creds(self):
        return self.credentials.get(self.venue, self.environment)

    def _redact(self, text: Any) -> str:
        return redact_text(str(text), self.credentials.known_values())

    def _auth_status(self) -> str:
        return str(self.credentials.status(self.venue, self.environment)["status"])

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def health(self) -> Dict[str, Any]:
        st = self._auth_status()
        return {"venue": self.venue, "environment": self.environment,
                "status": "NOT_CONFIGURED" if st != CONFIGURED else ("UNKNOWN" if self.last_ok_ns is None else "OK"),
                "data_source": "UNAVAILABLE" if self.last_ok_ns is None else "REAL_RUNTIME",
                "last_ok_ns": self.last_ok_ns, "last_error": self.last_error}

    def capabilities(self) -> Dict[str, Any]:
        creds_ok = self._auth_status() == CONFIGURED
        live_creds = str(self.credentials.status(self.venue, "LIVE")["status"])
        sbx_creds = str(self.credentials.status(self.venue, "SANDBOX")["status"])
        can_read = creds_ok and self.transport is not None
        return {"venue": self.venue, "environment": self.environment, "credentials": live_creds,
                "sandbox_credentials": sbx_creds, "public_market_data": self.PUBLIC_MD,
                "account_read": can_read,
                # Live submit is impossible while locked; sandbox submit needs sandbox creds + transport.
                "order_submit": can_read and self.environment == "SANDBOX",
                "order_cancel": can_read and self.environment == "SANDBOX",
                "private_stream": False, "sandbox_available": True, "live_available": False,
                "atomic_replace": False, "execution_mode": "LIVE_LOCKED"}

    def _http(self, method: str, path: str, params=None, body=None, signed=False, weight=1.0,
              mutating=False, headers=None) -> Any:
        if self.transport is None:
            raise TransportNotConfigured("no transport configured (no network available by default)")
        try:
            self.rate.acquire(weight)
        except RateLimited:
            raise
        params, headers = dict(params or {}), dict(headers or {})
        if signed:
            try:
                params, body, headers = self._sign(method, path, params, body, headers)
            except CredentialsNotConfigured as e:
                raise AuthFailure(f"{self.venue} credentials not configured") from e
        url = self.base_url + path
        try:
            resp = self.transport.request(method, url, headers=headers, params=params or None,
                                          json_body=body, timeout_s=10.0)
        except TransportConnectError as e:
            raise VenueUnavailable(self._redact(e), pre_send=True)
        except TransportTimeout as e:
            msg = self._redact(e)
            if mutating and e.sent:
                raise UnknownOutcomeError(msg)
            raise VenueUnavailable(msg, pre_send=not e.sent)
        except Exception as e:  # ambiguous after possible send
            msg = self._redact(e)
            if mutating:
                raise UnknownOutcomeError(msg)
            raise VenueUnavailable(msg, pre_send=False)
        return self._handle(resp, mutating)

    def _handle(self, resp: HttpResponse, mutating: bool) -> Any:
        if resp.status in (418, 429):
            ra = _f(resp.headers.get("Retry-After")) or 1.0
            self.rate.penalize(ra)
            raise RateLimited(ra, "venue rate limit")
        if resp.status in (401, 403):
            raise AuthFailure(f"{self.venue} authentication failed (HTTP {resp.status})")
        if resp.status >= 500:
            if mutating:
                raise UnknownOutcomeError(f"{self.venue} HTTP {resp.status} (outcome unknown)")
            raise VenueUnavailable(f"{self.venue} HTTP {resp.status}", pre_send=False)
        self._raise_for_body(resp)
        self.last_ok_ns = time.time_ns()
        return resp.body

    def _raise_for_body(self, resp: HttpResponse) -> None:  # per venue
        if resp.status >= 400:
            raise InvalidOrder(f"{self.venue} HTTP {resp.status}", code=str(resp.status))

    def _sign(self, method, path, params, body, headers):  # per venue
        return params, body, headers

    def fetch_instruments(self) -> List[InstrumentMeta]:  # public, per venue
        raise NotImplementedError

    def get_balances(self) -> Dict[str, Any]:
        acct = self.get_account()
        return {"equity": acct.equity, "available": acct.available_balance, "status": acct.status}


def _norm_order(client_id, venue_id, symbol, side, qty, filled, status) -> Dict[str, Any]:
    return {"client_order_id": client_id, "venue_order_id": str(venue_id) if venue_id is not None else None,
            "symbol": symbol, "side": side, "qty": _f(qty), "filled": _f(filled) or 0.0, "status": status}


# ============================================================ Binance USD-M
class BinanceUSDMAdapter(RestAdapter):
    venue = "binance_perp"
    PUBLIC_MD = True
    BASE = {"LIVE": "https://fapi.binance.com", "SANDBOX": "https://testnet.binancefuture.com"}
    STATUS = {"NEW": "NEW", "PARTIALLY_FILLED": "PARTIALLY_FILLED", "FILLED": "FILLED", "CANCELED": "CANCELED",
              "EXPIRED": "EXPIRED", "REJECTED": "REJECTED", "NEW_INSURANCE": "NEW", "NEW_ADL": "NEW"}

    def _sign(self, method, path, params, body, headers):
        key, secret = self._creds()
        params["timestamp"] = self._now_ms()
        params["recvWindow"] = 5000
        query = urllib.parse.urlencode(params)
        params["signature"] = hmac.new(secret.reveal().encode(), query.encode(), hashlib.sha256).hexdigest()
        headers["X-MBX-APIKEY"] = key.reveal()
        return params, body, headers

    def _raise_for_body(self, resp: HttpResponse) -> None:
        if resp.status >= 400:
            code = (resp.body or {}).get("code") if isinstance(resp.body, dict) else None
            msg = (resp.body or {}).get("msg", "") if isinstance(resp.body, dict) else ""
            if code in (-2014, -2015, -1022, -1002):
                raise AuthFailure(f"binance auth error {code}", code=str(code))
            if code == -1021:
                raise AdapterError("binance timestamp outside recvWindow (clock drift)", FailureClass.NON_RETRYABLE, code="-1021")
            raise InvalidOrder(f"binance error {code}: {self._redact(msg)}", code=str(code))

    def get_server_time(self) -> int:
        return int(self._http("GET", "/fapi/v1/time")["serverTime"])

    def get_account(self) -> AccountSnapshot:
        if self._auth_status() != CONFIGURED:
            return AccountSnapshot(venue=self.venue)
        b = self._http("GET", "/fapi/v2/account", signed=True, weight=5)
        return AccountSnapshot(venue=self.venue, account_id=None, equity=_f(b.get("totalMarginBalance")),
                               available_balance=_f(b.get("availableBalance")),
                               margin_used=_f(b.get("totalInitialMargin")), positions=self.get_positions(),
                               open_orders=self.get_open_orders(), timestamp_ns=time.time_ns(),
                               data_source="SANDBOX" if self.environment == "SANDBOX" else "REAL_RUNTIME",
                               status="KNOWN")

    def get_positions(self) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/fapi/v2/positionRisk", signed=True, weight=5)
        return [{"symbol": r["symbol"], "quantity": float(r["positionAmt"]), "entry_price": _f(r.get("entryPrice"))}
                for r in rows if float(r.get("positionAmt", 0) or 0) != 0]

    def _order(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return _norm_order(r.get("clientOrderId"), r.get("orderId"), r.get("symbol"), r.get("side"),
                           r.get("origQty"), r.get("executedQty"), self.STATUS.get(r.get("status"), "UNKNOWN"))

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return [self._order(r) for r in self._http("GET", "/fapi/v1/openOrders", signed=True, weight=40)]

    def get_order(self, client_order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            return self._order(self._http("GET", "/fapi/v1/order", {"symbol": symbol, "origClientOrderId": client_order_id},
                                          signed=True))
        except InvalidOrder as e:
            if e.code == "-2013":
                return None  # venue definitively reports: order does not exist
            raise

    def get_fills(self, symbol=None, since_ns=None) -> List[Dict[str, Any]]:
        if not symbol:
            raise AdapterError("binance userTrades requires a symbol", FailureClass.NON_RETRYABLE)
        params: Dict[str, Any] = {"symbol": symbol}
        if since_ns:
            params["startTime"] = int(since_ns // 1_000_000)
        return [{"venue_trade_id": str(t["id"]), "venue_order_id": str(t["orderId"]), "client_order_id": None,
                 "symbol": t["symbol"], "side": t.get("side"), "price": float(t["price"]), "qty": float(t["qty"]),
                 "fee": float(t["commission"]), "fee_asset": t["commissionAsset"], "is_taker": not t.get("maker", False),
                 "timestamp_ns": int(t["time"]) * 1_000_000}
                for t in self._http("GET", "/fapi/v1/userTrades", params, signed=True, weight=5)]

    def serialize_order(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        p: Dict[str, Any] = {"symbol": meta.venue_symbol, "side": intent.side, "type": intent.order_type,
                             "quantity": fnum(intent.quantity), "newClientOrderId": intent.client_order_id,
                             "reduceOnly": "true" if intent.reduce_only else "false", "newOrderRespType": "RESULT"}
        if intent.order_type == "LIMIT":
            p["price"] = fnum(intent.limit_price)
            p["timeInForce"] = "GTX" if intent.post_only else intent.time_in_force
        return p

    def submit_order(self, permit, intent, meta) -> Dict[str, Any]:
        self._check_permit(permit, "SUBMIT", intent.client_order_id)
        r = self._http("POST", "/fapi/v1/order", self.serialize_order(intent, meta), signed=True, mutating=True)
        o = self._order(r)
        return {"venue_order_id": o["venue_order_id"], "status": o["status"], "fills": []}

    def cancel_order(self, permit, client_order_id, symbol) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL", client_order_id)
        try:
            r = self._http("DELETE", "/fapi/v1/order", {"symbol": symbol, "origClientOrderId": client_order_id},
                           signed=True, mutating=True)
        except InvalidOrder as e:
            if e.code == "-2011":
                raise InvalidOrder("cancel rejected: unknown/finished order", code="CANCEL_REJECTED")
            raise
        return {"status": self.STATUS.get(r.get("status"), "CANCELED"), "fills": []}

    def cancel_all(self, permit, symbol=None) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL_ALL")
        if not symbol:
            raise AdapterError("binance allOpenOrders requires a symbol", FailureClass.NON_RETRYABLE)
        self._http("DELETE", "/fapi/v1/allOpenOrders", {"symbol": symbol}, signed=True, mutating=True)
        return {"canceled": None}

    def fetch_instruments(self) -> List[InstrumentMeta]:
        out = []
        for s in self._http("GET", "/fapi/v1/exchangeInfo", weight=10).get("symbols", []):
            f = {x["filterType"]: x for x in s.get("filters", [])}
            if "PRICE_FILTER" not in f or "LOT_SIZE" not in f:
                continue
            out.append(InstrumentMeta(
                symbol=s["symbol"], venue=self.venue, venue_symbol=s["symbol"],
                tick_size=float(f["PRICE_FILTER"]["tickSize"]), step_size=float(f["LOT_SIZE"]["stepSize"]),
                min_qty=float(f["LOT_SIZE"]["minQty"]),
                min_notional=float((f.get("MIN_NOTIONAL") or {}).get("notional", 0) or 0),
                contract_multiplier=1.0, margin_type="LINEAR", base_asset=s["baseAsset"],
                quote_asset=s["quoteAsset"], margin_asset=s.get("marginAsset", s["quoteAsset"])))
        return out

    def normalize_private_event(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        if raw.get("e") == "ORDER_TRADE_UPDATE":
            o = raw["o"]
            ev = [{"type": "ORDER", "client_order_id": o.get("c"), "venue_order_id": str(o.get("i")),
                   "status": self.STATUS.get(o.get("X"), "UNKNOWN"), "symbol": o.get("s")}]
            if o.get("x") == "TRADE":
                ev.append({"type": "FILL", "client_order_id": o.get("c"), "venue_order_id": str(o.get("i")),
                           "venue_trade_id": str(o.get("t")), "symbol": o.get("s"), "side": o.get("S"),
                           "price": float(o["L"]), "qty": float(o["l"]), "fee": float(o.get("n", 0) or 0),
                           "fee_asset": o.get("N", "USDT"), "is_taker": not o.get("m", False),
                           "timestamp_ns": int(raw.get("T", o.get("T", 0))) * 1_000_000})
            return ev
        if raw.get("e") == "ACCOUNT_UPDATE":
            return [{"type": "ACCOUNT", "raw_keys": sorted(raw.get("a", {}).keys())}]
        return []


# ================================================================== Bybit v5
class BybitAdapter(RestAdapter):
    venue = "bybit"
    PUBLIC_MD = "UNKNOWN"
    BASE = {"LIVE": "https://api.bybit.com", "SANDBOX": "https://api-testnet.bybit.com"}
    STATUS = {"New": "NEW", "PartiallyFilled": "PARTIALLY_FILLED", "Filled": "FILLED", "Cancelled": "CANCELED",
              "PartiallyFilledCanceled": "CANCELED", "Rejected": "REJECTED", "Deactivated": "EXPIRED",
              "Untriggered": "NEW", "Created": "NEW"}

    def _sign(self, method, path, params, body, headers):
        key, secret = self._creds()
        ts, recv = str(self._now_ms()), "5000"
        if method == "GET":
            payload = urllib.parse.urlencode(params)
        else:
            payload = json.dumps(body, separators=(",", ":")) if body is not None else ""
        sig = hmac.new(secret.reveal().encode(), (ts + key.reveal() + recv + payload).encode(),
                       hashlib.sha256).hexdigest()
        headers.update({"X-BAPI-API-KEY": key.reveal(), "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": recv,
                        "X-BAPI-SIGN": sig})
        return params, body, headers

    def _raise_for_body(self, resp: HttpResponse) -> None:
        b = resp.body if isinstance(resp.body, dict) else {}
        code = b.get("retCode", 0 if resp.status < 400 else resp.status)
        if code == 0:
            return
        if code in (10003, 10004, 10005, 10007):
            raise AuthFailure(f"bybit auth error {code}", code=str(code))
        if code == 10006:
            self.rate.penalize(1.0)
            raise RateLimited(1.0, "bybit rate limit")
        raise InvalidOrder(f"bybit error {code}: {self._redact(b.get('retMsg', ''))}", code=str(code))

    def get_server_time(self) -> int:
        b = self._http("GET", "/v5/market/time")
        res = b.get("result", {}) if isinstance(b, dict) else {}
        if "timeNano" in res:
            return int(res["timeNano"]) // 1_000_000
        if "timeSecond" in res:
            return int(res["timeSecond"]) * 1000
        return int(b.get("time") or 0)

    def get_account(self) -> AccountSnapshot:
        if self._auth_status() != CONFIGURED:
            return AccountSnapshot(venue=self.venue)
        r = self._http("GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}, signed=True)["result"]["list"][0]
        return AccountSnapshot(venue=self.venue, equity=_f(r.get("totalEquity")),
                               available_balance=_f(r.get("totalAvailableBalance")),
                               margin_used=_f(r.get("totalInitialMargin")), positions=self.get_positions(),
                               open_orders=self.get_open_orders(), timestamp_ns=time.time_ns(),
                               data_source="SANDBOX" if self.environment == "SANDBOX" else "REAL_RUNTIME",
                               status="KNOWN")

    def get_positions(self) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/v5/position/list", {"category": "linear", "settleCoin": "USDT"},
                          signed=True)["result"]["list"]
        out = []
        for r in rows:
            sz = float(r.get("size") or 0)
            if sz:
                out.append({"symbol": r["symbol"], "quantity": sz if r.get("side") == "Buy" else -sz,
                            "entry_price": _f(r.get("avgPrice"))})
        return out

    def _order(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return _norm_order(r.get("orderLinkId") or None, r.get("orderId"), r.get("symbol"),
                           (r.get("side") or "").upper(), r.get("qty"), r.get("cumExecQty"),
                           self.STATUS.get(r.get("orderStatus"), "UNKNOWN"))

    def get_open_orders(self) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/v5/order/realtime", {"category": "linear", "settleCoin": "USDT", "openOnly": 0},
                          signed=True)["result"]["list"]
        return [self._order(r) for r in rows if self.STATUS.get(r.get("orderStatus")) in ("NEW", "PARTIALLY_FILLED")]

    def get_order(self, client_order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        for path in ("/v5/order/realtime", "/v5/order/history"):
            rows = self._http("GET", path, {"category": "linear", "symbol": symbol, "orderLinkId": client_order_id},
                              signed=True)["result"]["list"]
            if rows:
                return self._order(rows[0])
        return None  # both live and historical queries succeeded and found nothing

    def get_fills(self, symbol=None, since_ns=None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"category": "linear"}
        if symbol:
            params["symbol"] = symbol
        if since_ns:
            params["startTime"] = int(since_ns // 1_000_000)
        rows = self._http("GET", "/v5/execution/list", params, signed=True)["result"]["list"]
        return [{"venue_trade_id": r["execId"], "venue_order_id": r["orderId"], "client_order_id": r.get("orderLinkId") or None,
                 "symbol": r["symbol"], "side": (r.get("side") or "").upper(), "price": float(r["execPrice"]),
                 "qty": float(r["execQty"]), "fee": float(r.get("execFee") or 0), "fee_asset": r.get("feeCurrency", "USDT"),
                 "is_taker": not r.get("isMaker", False), "timestamp_ns": int(r["execTime"]) * 1_000_000} for r in rows]

    def serialize_order(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        tif = "PostOnly" if intent.post_only else intent.time_in_force
        if tif == "GTX":
            tif = "PostOnly"
        body: Dict[str, Any] = {"category": "linear", "symbol": meta.venue_symbol,
                                "side": "Buy" if intent.side == "BUY" else "Sell",
                                "orderType": "Limit" if intent.order_type == "LIMIT" else "Market",
                                "qty": fnum(intent.quantity), "orderLinkId": intent.client_order_id,
                                "reduceOnly": intent.reduce_only}
        if intent.order_type == "LIMIT":
            body["price"] = fnum(intent.limit_price)
            body["timeInForce"] = tif
        return body

    def submit_order(self, permit, intent, meta) -> Dict[str, Any]:
        self._check_permit(permit, "SUBMIT", intent.client_order_id)
        r = self._http("POST", "/v5/order/create", body=self.serialize_order(intent, meta), signed=True, mutating=True)
        return {"venue_order_id": r["result"]["orderId"], "status": "NEW", "fills": []}

    def cancel_order(self, permit, client_order_id, symbol) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL", client_order_id)
        try:
            self._http("POST", "/v5/order/cancel", body={"category": "linear", "symbol": symbol,
                                                        "orderLinkId": client_order_id}, signed=True, mutating=True)
        except InvalidOrder as e:
            if e.code in ("110001", "110010", "110020"):
                raise InvalidOrder("cancel rejected: unknown/finished order", code="CANCEL_REJECTED")
            raise
        return {"status": "CANCELED", "fills": []}

    def cancel_all(self, permit, symbol=None) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL_ALL")
        body = {"category": "linear", **({"symbol": symbol} if symbol else {"settleCoin": "USDT"})}
        self._http("POST", "/v5/order/cancel-all", body=body, signed=True, mutating=True)
        return {"canceled": None}

    def fetch_instruments(self) -> List[InstrumentMeta]:
        out = []
        for s in self._http("GET", "/v5/market/instruments-info", {"category": "linear"})["result"]["list"]:
            out.append(InstrumentMeta(
                symbol=s["symbol"], venue=self.venue, venue_symbol=s["symbol"],
                tick_size=float(s["priceFilter"]["tickSize"]), step_size=float(s["lotSizeFilter"]["qtyStep"]),
                min_qty=float(s["lotSizeFilter"]["minOrderQty"]),
                min_notional=float(s["lotSizeFilter"].get("minNotionalValue", 0) or 0), contract_multiplier=1.0,
                margin_type="LINEAR", base_asset=s["baseCoin"], quote_asset=s["quoteCoin"],
                margin_asset=s.get("settleCoin", s["quoteCoin"])))
        return out

    def normalize_private_event(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        topic, out = raw.get("topic", ""), []
        for d in raw.get("data", []) or []:
            if topic == "order":
                out.append({"type": "ORDER", "client_order_id": d.get("orderLinkId"), "venue_order_id": d.get("orderId"),
                            "status": self.STATUS.get(d.get("orderStatus"), "UNKNOWN"), "symbol": d.get("symbol")})
            elif topic == "execution":
                out.append({"type": "FILL", "client_order_id": d.get("orderLinkId"), "venue_order_id": d.get("orderId"),
                            "venue_trade_id": d.get("execId"), "symbol": d.get("symbol"),
                            "side": (d.get("side") or "").upper(), "price": float(d["execPrice"]),
                            "qty": float(d["execQty"]), "fee": float(d.get("execFee") or 0), "fee_asset": "USDT",
                            "is_taker": not d.get("isMaker", False), "timestamp_ns": int(d["execTime"]) * 1_000_000})
            elif topic == "position":
                out.append({"type": "POSITION", "symbol": d.get("symbol")})
            elif topic == "wallet":
                out.append({"type": "ACCOUNT"})
        return out


# ================================================================== Deribit
class DeribitAdapter(RestAdapter):
    venue = "deribit"
    PUBLIC_MD = True
    BASE = {"LIVE": "https://www.deribit.com/api/v2", "SANDBOX": "https://test.deribit.com/api/v2"}
    STATE = {"open": "NEW", "filled": "FILLED", "rejected": "REJECTED", "cancelled": "CANCELED",
             "untriggered": "NEW", "expired": "EXPIRED"}

    def __init__(self, *a, currency: str = "BTC", **kw):
        super().__init__(*a, **kw)
        self.currency = currency
        self._token: Optional[str] = None
        self._token_exp_ms = 0

    def _sign(self, method, path, params, body, headers):
        now = self._now_ms()
        if not self._token or now >= self._token_exp_ms:
            cid, csec = self._creds()
            r = self._http("GET", "/public/auth", {"grant_type": "client_credentials", "client_id": cid.reveal(),
                                                    "client_secret": csec.reveal()})
            self._token = r["result"]["access_token"]
            self._token_exp_ms = now + int(r["result"].get("expires_in", 600)) * 1000 - 30_000
        headers["Authorization"] = f"Bearer {self._token}"
        return params, body, headers

    def _raise_for_body(self, resp: HttpResponse) -> None:
        b = resp.body if isinstance(resp.body, dict) else {}
        err = b.get("error")
        if not err and resp.status < 400:
            return
        code = (err or {}).get("code", resp.status)
        if code in (13004, 13009, 13010):
            raise AuthFailure(f"deribit auth error {code}", code=str(code))
        if code == 10028:
            self.rate.penalize(1.0)
            raise RateLimited(1.0, "deribit rate limit")
        raise InvalidOrder(f"deribit error {code}: {self._redact((err or {}).get('message', ''))}", code=str(code))

    def get_server_time(self) -> int:
        return int(self._http("GET", "/public/get_time")["result"])

    def get_account(self) -> AccountSnapshot:
        if self._auth_status() != CONFIGURED:
            return AccountSnapshot(venue=self.venue)
        r = self._http("GET", "/private/get_account_summary", {"currency": self.currency}, signed=True)["result"]
        return AccountSnapshot(venue=self.venue, account_id=f"deribit:{self.currency}", equity=_f(r.get("equity")),
                               available_balance=_f(r.get("available_funds")), margin_used=_f(r.get("initial_margin")),
                               positions=self.get_positions(), open_orders=self.get_open_orders(),
                               timestamp_ns=time.time_ns(), margin_asset=self.currency,
                               data_source="SANDBOX" if self.environment == "SANDBOX" else "REAL_RUNTIME",
                               status="KNOWN")

    def get_positions(self) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/private/get_positions", {"currency": self.currency}, signed=True)["result"]
        return [{"symbol": r["instrument_name"], "quantity": float(r["size"]), "entry_price": _f(r.get("average_price"))}
                for r in rows if float(r.get("size") or 0) != 0]

    def _order(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return _norm_order(r.get("label") or None, r.get("order_id"), r.get("instrument_name"),
                           (r.get("direction") or "").upper(), r.get("amount"), r.get("filled_amount"),
                           self.STATE.get(r.get("order_state"), "UNKNOWN"))

    def get_open_orders(self) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/private/get_open_orders_by_currency", {"currency": self.currency}, signed=True)["result"]
        return [self._order(r) for r in rows]

    def get_order(self, client_order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        rows = self._http("GET", "/private/get_open_orders_by_label",
                          {"currency": self.currency, "label": client_order_id}, signed=True)["result"]
        if rows:
            return self._order(rows[0])
        hist = self._http("GET", "/private/get_order_history_by_currency",
                          {"currency": self.currency, "count": 100}, signed=True)["result"]
        for r in hist:
            if r.get("label") == client_order_id:
                return self._order(r)
        return None

    def get_fills(self, symbol=None, since_ns=None) -> List[Dict[str, Any]]:
        rows = self._http("GET", "/private/get_user_trades_by_currency", {"currency": self.currency, "count": 100},
                          signed=True)["result"]["trades"]
        return [{"venue_trade_id": t["trade_id"], "venue_order_id": t["order_id"], "client_order_id": t.get("label") or None,
                 "symbol": t["instrument_name"], "side": t["direction"].upper(), "price": float(t["price"]),
                 "qty": float(t["amount"]), "fee": float(t.get("fee", 0)), "fee_asset": t.get("fee_currency", self.currency),
                 "is_taker": t.get("liquidity") == "T", "timestamp_ns": int(t["timestamp"]) * 1_000_000}
                for t in rows if symbol in (None, t["instrument_name"])]

    def serialize_order(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        tif = {"GTC": "good_til_cancelled", "IOC": "immediate_or_cancel", "FOK": "fill_or_kill",
               "GTX": "good_til_cancelled"}[intent.time_in_force]
        p: Dict[str, Any] = {"instrument_name": meta.venue_symbol, "amount": fnum(intent.quantity),
                             "type": intent.order_type.lower(), "label": intent.client_order_id[:64],
                             "reduce_only": "true" if intent.reduce_only else "false"}
        if intent.order_type == "LIMIT":
            p["price"] = fnum(intent.limit_price)
            p["time_in_force"] = tif
            p["post_only"] = "true" if (intent.post_only or intent.time_in_force == "GTX") else "false"
        return p

    def submit_order(self, permit, intent, meta) -> Dict[str, Any]:
        self._check_permit(permit, "SUBMIT", intent.client_order_id)
        path = "/private/buy" if intent.side == "BUY" else "/private/sell"
        r = self._http("GET", path, self.serialize_order(intent, meta), signed=True, mutating=True)["result"]
        o = r["order"]
        return {"venue_order_id": o["order_id"], "status": self.STATE.get(o.get("order_state"), "NEW"), "fills": []}

    def cancel_order(self, permit, client_order_id, symbol) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL", client_order_id)
        try:
            self._http("GET", "/private/cancel_by_label", {"label": client_order_id, "currency": self.currency},
                       signed=True, mutating=True)
        except InvalidOrder as e:
            if e.code == "11044":
                raise InvalidOrder("cancel rejected: not open", code="CANCEL_REJECTED")
            raise
        return {"status": "CANCELED", "fills": []}

    def cancel_all(self, permit, symbol=None) -> Dict[str, Any]:
        self._check_permit(permit, "CANCEL_ALL")
        if symbol:
            self._http("GET", "/private/cancel_all_by_instrument", {"instrument_name": symbol}, signed=True, mutating=True)
        else:
            self._http("GET", "/private/cancel_all_by_currency", {"currency": self.currency}, signed=True, mutating=True)
        return {"canceled": None}

    def fetch_instruments(self) -> List[InstrumentMeta]:
        out = []
        for s in self._http("GET", "/public/get_instruments", {"currency": self.currency, "kind": "future"})["result"]:
            out.append(InstrumentMeta(
                symbol=s["instrument_name"], venue=self.venue, venue_symbol=s["instrument_name"],
                tick_size=float(s["tick_size"]), step_size=float(s.get("min_trade_amount", s.get("contract_size", 1))),
                min_qty=float(s.get("min_trade_amount", 1)), min_notional=0.0,
                contract_multiplier=float(s.get("contract_size", 1)),
                margin_type="INVERSE" if s.get("settlement_currency", s["base_currency"]) == s["base_currency"] else "LINEAR",
                base_asset=s["base_currency"], quote_asset=s.get("quote_currency", "USD"),
                margin_asset=s.get("settlement_currency", s["base_currency"])))
        return out

    def normalize_private_event(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = raw.get("params") or {}
        ch, data, out = params.get("channel", ""), params.get("data"), []
        if ch.startswith("user.orders"):
            for d in (data if isinstance(data, list) else [data]):
                out.append({"type": "ORDER", "client_order_id": d.get("label"), "venue_order_id": d.get("order_id"),
                            "status": self.STATE.get(d.get("order_state"), "UNKNOWN"), "symbol": d.get("instrument_name")})
        elif ch.startswith("user.trades"):
            for t in data or []:
                out.append({"type": "FILL", "client_order_id": t.get("label"), "venue_order_id": t.get("order_id"),
                            "venue_trade_id": t["trade_id"], "symbol": t["instrument_name"],
                            "side": t["direction"].upper(), "price": float(t["price"]), "qty": float(t["amount"]),
                            "fee": float(t.get("fee", 0)), "fee_asset": t.get("fee_currency", self.currency),
                            "is_taker": t.get("liquidity") == "T", "timestamp_ns": int(t["timestamp"]) * 1_000_000})
        elif ch.startswith("user.portfolio"):
            out.append({"type": "ACCOUNT"})
        return out
