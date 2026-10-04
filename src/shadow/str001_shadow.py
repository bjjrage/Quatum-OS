"""STR-001 SHADOW runner: Polymarket crypto-threshold markets vs the Deribit option surface.

SHADOW means: real market data in, fair value and a *would-trade* decision out, and NOTHING is sent
anywhere. Every evaluation is appended to JSONL with all of its inputs so the edge can be measured
later (see ``score_shadow_log``) without trusting any simulator.

Decision rule (executable prices, not mids):
    fair      = Deribit-implied P(YES) from the interpolated surface
    band      = fair recomputed with sigma +/- ``iv_band`` (default 2 vol points)
    BUY_YES   if  (band_lo - ask)  - costs >= min_edge
    BUY_NO    if  (bid - band_hi)  - costs >= min_edge      (selling YES == buying NO)
Costs = fee_bps * price + slippage_bps (probability units). Markets that are not clean digitals, have a
stale / wide / thin book, or sit at extreme prices are skipped with an explicit reason.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from src.collectors.polymarket_recorder import normalize_book_levels
from src.quant.deribit_surface import DeribitSurface
from src.research.market_mapping import MappedMarket, RejectedMarket, map_gamma_markets


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    ts_ns: Optional[int] = None


@dataclass(frozen=True)
class ShadowConfig:
    min_edge_bps: float = 200.0         # net, after costs and after the IV band
    poly_fee_bps: float = 0.0           # fee on notional; Polymarket crypto markets are fee-free unless stated
    slippage_bps: float = 50.0
    iv_band: float = 0.02               # +/- 2 vol points
    max_spread: float = 0.06
    min_top_size: float = 50.0          # shares at the touch
    max_quote_age_s: float = 90.0
    min_price: float = 0.03
    max_price: float = 0.97
    min_hours_to_resolution: float = 2.0
    max_days_to_resolution: float = 21.0


def _fair_yes(mm: MappedMarket, surf: DeribitSurface, iv_shift: float) -> Tuple[Optional[float], Dict[str, Any], str]:
    p = mm.parsed
    target = p.resolve_utc
    if p.kind in ("ABOVE", "BELOW"):
        d, why = surf.digital_above(target, p.strike_lo, iv_shift)
        if d is None:
            return None, {}, why
        prob = d.probability if p.kind == "ABOVE" else 1.0 - d.probability
        return prob, {"forward": d.forward, "strike": p.strike_lo, "t_years": d.t_years, "sigma": d.sigma,
                      "dsigma_dK": d.dsigma_dk, "expiry_lo": d.expiry_lo.isoformat(),
                      "expiry_hi": d.expiry_hi.isoformat()}, ""
    # RANGE: P(lo < S <= hi) = P(S > lo) - P(S > hi)
    d_lo, why = surf.digital_above(target, p.strike_lo, iv_shift)
    d_hi, why2 = surf.digital_above(target, float(p.strike_hi), iv_shift)
    if d_lo is None or d_hi is None:
        return None, {}, why or why2
    prob = max(0.0, d_lo.probability - d_hi.probability)
    return prob, {"forward": d_lo.forward, "strike_lo": p.strike_lo, "strike_hi": p.strike_hi,
                  "t_years": d_lo.t_years, "sigma_lo": d_lo.sigma, "sigma_hi": d_hi.sigma}, ""


def evaluate_market(mm: MappedMarket, surface: Optional[DeribitSurface], quote: Optional[Quote],
                    now: datetime, cfg: ShadowConfig = ShadowConfig()) -> Dict[str, Any]:
    """Pure function: one shadow evaluation record (never raises for bad market data)."""
    rec: Dict[str, Any] = {
        "ts_utc": now.isoformat(), "market_id": mm.market_id, "question": mm.question,
        "underlying": mm.parsed.underlying, "kind": mm.parsed.kind, "yes_token_id": mm.yes_token_id,
        "resolve_utc": mm.parsed.resolve_utc.isoformat(), "action": "NONE",
    }
    hours = (mm.parsed.resolve_utc - now).total_seconds() / 3600.0
    if hours < cfg.min_hours_to_resolution:
        return {**rec, "status": "SKIPPED", "reason": "TOO_CLOSE_TO_RESOLUTION"}
    if hours > cfg.max_days_to_resolution * 24.0:
        return {**rec, "status": "SKIPPED", "reason": "TOO_FAR_FROM_RESOLUTION"}
    if surface is None:
        return {**rec, "status": "SKIPPED", "reason": "NO_DERIBIT_SURFACE"}
    fair, inputs, why = _fair_yes(mm, surface, 0.0)
    if fair is None:
        return {**rec, "status": "SKIPPED", "reason": why}
    f_hi, _, _ = _fair_yes(mm, surface, +cfg.iv_band)
    f_lo, _, _ = _fair_yes(mm, surface, -cfg.iv_band)
    cands = [x for x in (fair, f_hi, f_lo) if x is not None]
    band_lo, band_hi = min(cands), max(cands)
    rec.update({"fair_yes": fair, "fair_band_lo": band_lo, "fair_band_hi": band_hi, "inputs": inputs})

    if quote is None:
        return {**rec, "status": "SKIPPED", "reason": "NO_POLYMARKET_QUOTE"}
    rec["quote"] = {"bid": quote.bid, "ask": quote.ask, "bid_size": quote.bid_size, "ask_size": quote.ask_size,
                    "ts_ns": quote.ts_ns}
    if not (0.0 < quote.bid <= quote.ask < 1.0 + 1e-9) or quote.ask - quote.bid > cfg.max_spread:
        return {**rec, "status": "SKIPPED", "reason": "BOOK_CROSSED_OR_SPREAD_TOO_WIDE"}
    if quote.ts_ns is not None and (now.timestamp() * 1e9 - quote.ts_ns) / 1e9 > cfg.max_quote_age_s:
        return {**rec, "status": "SKIPPED", "reason": "QUOTE_STALE"}
    mid = 0.5 * (quote.bid + quote.ask)
    if not (cfg.min_price <= mid <= cfg.max_price):
        return {**rec, "status": "SKIPPED", "reason": "EXTREME_PRICE"}
    if quote.bid_size < cfg.min_top_size or quote.ask_size < cfg.min_top_size:
        return {**rec, "status": "SKIPPED", "reason": "THIN_BOOK"}

    cost_buy = (cfg.poly_fee_bps * quote.ask + cfg.slippage_bps) / 1e4
    cost_sell = (cfg.poly_fee_bps * (1.0 - quote.bid) + cfg.slippage_bps) / 1e4
    edge_buy_yes = (band_lo - quote.ask) - cost_buy
    edge_buy_no = (quote.bid - band_hi) - cost_sell
    rec.update({"mid": mid, "edge_buy_yes_bps": edge_buy_yes * 1e4, "edge_buy_no_bps": edge_buy_no * 1e4,
                "status": "PRICED"})
    if edge_buy_yes * 1e4 >= cfg.min_edge_bps and edge_buy_yes >= edge_buy_no:
        rec["action"], rec["entry_price"] = "BUY_YES", quote.ask
    elif edge_buy_no * 1e4 >= cfg.min_edge_bps:
        rec["action"], rec["entry_price"] = "BUY_NO", 1.0 - quote.bid
    return rec


# --------------------------------------------------------------------------- scoring (the actual verdict)
def score_shadow_log(records: Iterable[Dict[str, Any]], outcomes_yes: Dict[str, int],
                     cfg: ShadowConfig = ShadowConfig()) -> Dict[str, Any]:
    """Settle logged shadow evaluations against realised outcomes.

    ``outcomes_yes``: market_id -> 1 if YES resolved true, else 0 (only resolved markets).
    * Calibration: Brier score of the Deribit-implied fair value vs the Polymarket mid, on every priced record.
    * Trades: first signal per (market, action), held to resolution, net of ``slippage`` (+ fee). One share each.
    """
    brier_fair: List[float] = []
    brier_mid: List[float] = []
    first: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in records:
        mid, fair, y = r.get("mid"), r.get("fair_yes"), outcomes_yes.get(r.get("market_id"))
        if r.get("status") != "PRICED" or y is None or mid is None or fair is None:
            continue
        brier_fair.append((fair - y) ** 2)
        brier_mid.append((mid - y) ** 2)
        if r.get("action") in ("BUY_YES", "BUY_NO"):
            first.setdefault((r["market_id"], r["action"]), r)
    pnls: List[float] = []
    for (mid_, action), r in first.items():
        y = outcomes_yes[mid_]
        entry = r["entry_price"]
        payoff = float(y) if action == "BUY_YES" else float(1 - y)
        cost = (cfg.poly_fee_bps * entry + cfg.slippage_bps) / 1e4
        pnls.append(payoff - entry - cost)
    n = len(pnls)
    mean = sum(pnls) / n if n else None
    sd = (sum((x - mean) ** 2 for x in pnls) / (n - 1)) ** 0.5 if n > 1 else None
    return {
        "priced_records": len(brier_fair),
        "brier_deribit_fair": sum(brier_fair) / len(brier_fair) if brier_fair else None,
        "brier_polymarket_mid": sum(brier_mid) / len(brier_mid) if brier_mid else None,
        "trades": n, "mean_pnl_per_share": mean,
        "t_stat": (mean / (sd / n ** 0.5)) if (mean is not None and sd) else None,
        "hit_rate": (sum(1 for x in pnls if x > 0) / n) if n else None,
        "note": "t_stat is naive: markets of the same expiry share one underlying move (cluster before trusting).",
    }


# --------------------------------------------------------------------------- live IO (REST polling)
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
CLOB_BOOKS = "https://clob.polymarket.com/books"
DERIBIT_SUMMARY = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"


def fetch_gamma_crypto_items(client) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for page in range(8):
        r = client.get(GAMMA_EVENTS, params={"limit": 100, "active": "true", "closed": "false",
                                             "tag_slug": "crypto", "offset": page * 100}, timeout=15.0)
        r.raise_for_status()
        events = r.json()
        if not isinstance(events, list) or not events:
            break
        for ev in events:
            items.extend(ev.get("markets") or [])
    return items


def fetch_polymarket_quotes(client, tokens: List[str]) -> Dict[str, Quote]:
    out: Dict[str, Quote] = {}
    for i in range(0, len(tokens), 50):
        chunk = tokens[i:i + 50]
        r = client.post(CLOB_BOOKS, json=[{"token_id": t} for t in chunk], timeout=15.0)
        r.raise_for_status()
        for bk in r.json():
            bp, bs, ap, asz = normalize_book_levels(bk.get("bids", []), bk.get("asks", []))
            if not bp or not ap:
                continue
            ts = bk.get("timestamp")
            ts_ns = None
            if ts:
                ts_ns = int(ts) * 1_000_000 if len(str(ts)) <= 13 else int(ts)
            out[str(bk.get("asset_id"))] = Quote(bp[0], ap[0], bs[0], asz[0], ts_ns)
    return out


def fetch_deribit_summaries(client, currency: str) -> List[Dict[str, Any]]:
    r = client.get(DERIBIT_SUMMARY, params={"currency": currency, "kind": "option"}, timeout=20.0)
    r.raise_for_status()
    return r.json().get("result", [])


class ShadowRunner:
    def __init__(self, out_dir: Path = Path("data/shadow"), cfg: ShadowConfig = ShadowConfig(),
                 cycle_s: float = 30.0, catalog_refresh_s: float = 900.0,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 sleep: Callable[[float], None] = time.sleep):
        self.out_dir, self.cfg, self.cycle_s = Path(out_dir), cfg, cycle_s
        self.catalog_refresh_s = catalog_refresh_s
        self.clock, self.sleep = clock, sleep
        self.mapped: List[MappedMarket] = []
        self.rejected: List[RejectedMarket] = []
        self._catalog_at: Optional[float] = None

    def _append(self, name: str, rec: Dict[str, Any]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        day = self.clock().strftime("%Y%m%d")
        with open(self.out_dir / f"{name}_{day}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    def refresh_catalog(self, client) -> None:
        self.mapped, self.rejected = map_gamma_markets(fetch_gamma_crypto_items(client))
        self._catalog_at = time.monotonic()
        reasons: Dict[str, int] = {}
        for r in self.rejected:
            reasons[r.reason] = reasons.get(r.reason, 0) + 1
        self._append("catalog", {"ts_utc": self.clock().isoformat(), "mapped": len(self.mapped),
                                 "rejected": len(self.rejected), "reject_reasons": reasons,
                                 "mapped_questions": [m.question for m in self.mapped][:200]})

    def run_cycle(self, client) -> List[Dict[str, Any]]:
        if self._catalog_at is None or time.monotonic() - self._catalog_at > self.catalog_refresh_s:
            self.refresh_catalog(client)
        now = self.clock()
        wanted = [m for m in self.mapped if self.cfg.min_hours_to_resolution <=
                  (m.parsed.resolve_utc - now).total_seconds() / 3600.0 <= self.cfg.max_days_to_resolution * 24.0]
        surfaces: Dict[str, Optional[DeribitSurface]] = {}
        for ccy in sorted({m.parsed.underlying for m in wanted}):
            try:
                surfaces[ccy] = DeribitSurface.from_summaries(fetch_deribit_summaries(client, ccy), ccy, now)
            except Exception as ex:  # a failing feed must never turn into a stale price
                surfaces[ccy] = None
                self._append("errors", {"ts_utc": now.isoformat(), "feed": f"deribit:{ccy}", "error": repr(ex)})
        try:
            quotes = fetch_polymarket_quotes(client, [m.yes_token_id for m in wanted])
        except Exception as ex:
            quotes = {}
            self._append("errors", {"ts_utc": now.isoformat(), "feed": "polymarket_books", "error": repr(ex)})
        out = []
        for m in wanted:
            rec = evaluate_market(m, surfaces.get(m.parsed.underlying), quotes.get(m.yes_token_id), now, self.cfg)
            self._append("str001_shadow", rec)
            out.append(rec)
        return out

    def run_forever(self, client) -> None:
        while True:
            try:
                self.run_cycle(client)
            except Exception as ex:
                self._append("errors", {"ts_utc": self.clock().isoformat(), "feed": "cycle", "error": repr(ex)})
            self.sleep(self.cycle_s)
