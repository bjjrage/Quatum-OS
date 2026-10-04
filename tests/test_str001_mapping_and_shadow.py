"""Tests for the STR-001 market mapping, Deribit surface and shadow decision logic."""
import asyncio
import math
from datetime import datetime, timedelta, timezone

import pytest

from src.collectors.polymarket_recorder import (PolymarketRecorder, is_crypto_market_question,
                                                normalize_book_levels)
from src.quant.black76 import norm_cdf
from src.quant.deribit_surface import DeribitSurface, parse_instrument
from src.research.market_mapping import map_gamma_market, parse_question
from src.shadow.str001_shadow import Quote, ShadowConfig, evaluate_market, score_shadow_log

NOW = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ question parsing
@pytest.mark.parametrize("q,end,kind,strike", [
    ("Will Bitcoin be above $110,000 on October 31?", "2026-10-31T16:00:00Z", "ABOVE", 110000.0),
    ("Will the price of Ethereum be below $3,500 on Oct 20, 2026?", "2026-10-20T16:00:00Z", "BELOW", 3500.0),
    ("Bitcoin above 95k on October 10?", "2026-10-10T00:00:00Z", "ABOVE", 95000.0),
])
def test_parse_valid_digitals(q, end, kind, strike):
    p, why = parse_question(q, end)
    assert p is not None, why
    assert p.kind == kind and p.strike_lo == strike
    # 12:00 ET on the question date, expressed in UTC (EDT in October => 16:00 UTC)
    assert p.resolve_utc.hour == 16 and p.resolve_utc.tzinfo is not None


def test_parse_between_range():
    p, why = parse_question("Will Bitcoin be between $108,000 and $110,000 on October 31?", "2026-10-31T16:00:00Z")
    assert p and p.kind == "RANGE" and (p.strike_lo, p.strike_hi) == (108000.0, 110000.0)


@pytest.mark.parametrize("q,end,reason", [
    ("Will Bitcoin hit $120,000 in October?", "2026-10-31T16:00:00Z", "BARRIER_TOUCH_MARKET_NOT_A_DIGITAL"),
    ("Will Bitcoin reach $150k by December 31?", "2026-12-31T16:00:00Z", "BARRIER_TOUCH_MARKET_NOT_A_DIGITAL"),
    ("Will Bitcoin dip to $80,000 this month?", "2026-10-31T16:00:00Z", "BARRIER_TOUCH_MARKET_NOT_A_DIGITAL"),
    ("Will Bitcoin or Ethereum be above $4,000 on October 31?", "2026-10-31T16:00:00Z", "UNDERLYING_UNKNOWN_OR_AMBIGUOUS"),
    ("Will the Lakers win tonight?", "2026-10-31T16:00:00Z", "UNDERLYING_UNKNOWN_OR_AMBIGUOUS"),
    ("Will Bitcoin be above $100,000?", "2026-10-31T00:00:00Z", "RESOLUTION_TIME_UNKNOWN"),
    ("Will Bitcoin be above $100,000 on October 5?", "2026-10-31T16:00:00Z", "QUESTION_DATE_DISAGREES_WITH_END_DATE"),
    ("Will Bitcoin be above $100,000 on October 31?", "", "END_DATE_MISSING"),
    ("Will Bitcoin close October 31 near $100,000?", "2026-10-31T16:00:00Z", "DIRECTION_UNKNOWN"),
])
def test_parse_rejections_are_explicit(q, end, reason):
    p, why = parse_question(q, end)
    assert p is None and why == reason


def test_gamma_market_requires_yes_no_binary():
    item = {"id": "1", "question": "Will Bitcoin be above $110,000 on October 31?",
            "endDate": "2026-10-31T16:00:00Z", "clobTokenIds": '["111","222"]', "outcomes": '["Yes","No"]'}
    mm, rej = map_gamma_market(item)
    assert mm and mm.yes_token_id == "111" and mm.no_token_id == "222"
    item["outcomes"] = '["Up","Down"]'
    mm, rej = map_gamma_market(item)
    assert mm is None and rej.reason == "NOT_A_YES_NO_BINARY_WITH_TWO_TOKENS"


# ------------------------------------------------------------------ Deribit surface
def _flat_surface(sigma_pct=50.0, spot=100_000.0):
    """Synthetic chain: flat vol, two expiries (Oct 9 and Oct 30 08:00 UTC), forward = spot."""
    rows = []
    for day in ("9OCT26", "30OCT26"):
        for strike in range(70_000, 135_001, 5_000):
            for cp in ("C", "P"):
                rows.append({"instrument_name": f"BTC-{day}-{strike}-{cp}", "mark_iv": sigma_pct,
                             "underlying_price": spot})
    return DeribitSurface.from_summaries(rows, "BTC", NOW)


def test_parse_instrument():
    ccy, exp, k, cp = parse_instrument("BTC-9OCT26-100000-C")
    assert (ccy, k, cp) == ("BTC", 100000.0, "C") and exp == datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)
    assert parse_instrument("BTC-PERPETUAL") is None


def test_flat_vol_digital_matches_closed_form():
    surf = _flat_surface()
    target = datetime(2026, 10, 20, 16, 0, tzinfo=timezone.utc)   # between the two expiries
    d, why = surf.digital_above(target, 105_000.0)
    assert d is not None, why
    t = (target - NOW).total_seconds() / (365 * 24 * 3600)
    d2 = (math.log(100_000 / 105_000) - 0.5 * 0.5 ** 2 * t) / (0.5 * math.sqrt(t))
    assert abs(d.probability - norm_cdf(d2)) < 0.01
    assert abs(d.sigma - 0.5) < 1e-6 and abs(d.dsigma_dk) < 1e-9


def test_surface_refuses_to_extrapolate():
    surf = _flat_surface()
    assert surf.digital_above(datetime(2026, 12, 1, 16, 0, tzinfo=timezone.utc), 100_000.0)[0] is None   # beyond last expiry
    assert surf.digital_above(datetime(2026, 10, 3, 15, 10, tzinfo=timezone.utc), 100_000.0)[0] is None  # too close
    d, why = surf.digital_above(datetime(2026, 10, 20, 16, 0, tzinfo=timezone.utc), 300_000.0)            # off the smile
    assert d is None and why in ("STRIKE_OUTSIDE_LISTED_SMILE", "SKEW_UNAVAILABLE_AT_SMILE_EDGE")


def test_expired_and_bad_rows_are_dropped():
    rows = [{"instrument_name": "BTC-1OCT26-100000-C", "mark_iv": 50, "underlying_price": 100000},   # already expired
            {"instrument_name": "BTC-9OCT26-100000-C", "mark_iv": float("nan"), "underlying_price": 100000},
            {"instrument_name": "BTC-9OCT26-100000-P", "mark_iv": 0, "underlying_price": 100000}]
    assert DeribitSurface.from_summaries(rows, "BTC", NOW).smiles == []


# ------------------------------------------------------------------ shadow decisions
def _market(strike=105_000.0, kind_word="above"):
    item = {"id": "m1", "question": f"Will Bitcoin be {kind_word} ${strike:,.0f} on October 20?",
            "endDate": "2026-10-20T16:00:00Z", "clobTokenIds": '["Y","N"]', "outcomes": '["Yes","No"]'}
    mm, rej = map_gamma_market(item)
    assert mm, rej
    return mm


def _q(bid, ask, size=500.0, ts=None):
    return Quote(bid, ask, size, size, ts if ts is not None else int(NOW.timestamp() * 1e9))


def test_shadow_buys_yes_when_market_is_cheap_and_no_trade_when_fair():
    surf, mm = _flat_surface(), _market()
    fair = evaluate_market(mm, surf, _q(0.30, 0.32), NOW)["fair_yes"]
    cheap = evaluate_market(mm, surf, _q(fair - 0.20, fair - 0.18), NOW)
    assert cheap["status"] == "PRICED" and cheap["action"] == "BUY_YES"
    rich = evaluate_market(mm, surf, _q(fair + 0.18, fair + 0.20), NOW)
    assert rich["action"] == "BUY_NO"
    flat = evaluate_market(mm, surf, _q(fair - 0.01, fair + 0.01), NOW)
    assert flat["action"] == "NONE"


def test_shadow_skips_unsafe_books():
    surf, mm = _flat_surface(), _market()
    assert evaluate_market(mm, surf, None, NOW)["reason"] == "NO_POLYMARKET_QUOTE"
    assert evaluate_market(mm, surf, _q(0.10, 0.30), NOW)["reason"] == "BOOK_CROSSED_OR_SPREAD_TOO_WIDE"
    assert evaluate_market(mm, surf, _q(0.30, 0.32, size=5.0), NOW)["reason"] == "THIN_BOOK"
    stale = int((NOW - timedelta(minutes=10)).timestamp() * 1e9)
    assert evaluate_market(mm, surf, _q(0.30, 0.32, ts=stale), NOW)["reason"] == "QUOTE_STALE"
    assert evaluate_market(mm, surf, _q(0.005, 0.01), NOW)["reason"] == "EXTREME_PRICE"
    assert evaluate_market(mm, None, _q(0.3, 0.32), NOW)["reason"] == "NO_DERIBIT_SURFACE"


def test_band_blocks_marginal_edges():
    """An edge smaller than the +/-2 vol-point uncertainty band must not trigger a trade."""
    surf, mm = _flat_surface(), _market()
    base = evaluate_market(mm, surf, _q(0.30, 0.32), NOW)
    lo, hi = base["fair_band_lo"], base["fair_band_hi"]
    assert hi - lo > 0.005
    ask = lo - 0.0205   # 205 bps below the band, but 50 bps of slippage leaves 155 bps (< 200 hurdle)
    r = evaluate_market(mm, surf, _q(ask - 0.02, ask), NOW)
    assert r["action"] == "NONE" and 100.0 < r["edge_buy_yes_bps"] < 200.0
    # while the point estimate alone would have looked tradable (that is exactly what the band prevents)
    assert (r["fair_yes"] - ask) * 1e4 - 50.0 > r["edge_buy_yes_bps"]
    ask2 = lo - 0.0305
    assert evaluate_market(mm, surf, _q(ask2 - 0.02, ask2), NOW)["action"] == "BUY_YES"


def test_scoring_settles_pnl_and_calibration():
    recs = [
        {"status": "PRICED", "market_id": "a", "mid": 0.40, "fair_yes": 0.60, "action": "BUY_YES", "entry_price": 0.42},
        {"status": "PRICED", "market_id": "a", "mid": 0.41, "fair_yes": 0.61, "action": "BUY_YES", "entry_price": 0.43},
        {"status": "PRICED", "market_id": "b", "mid": 0.70, "fair_yes": 0.50, "action": "BUY_NO", "entry_price": 0.31},
        {"status": "SKIPPED", "market_id": "c"},
    ]
    s = score_shadow_log(recs, {"a": 1, "b": 0}, ShadowConfig(slippage_bps=0.0))
    assert s["trades"] == 2                                  # only the FIRST signal per (market, action)
    assert abs(s["mean_pnl_per_share"] - ((1 - 0.42) + (1 - 0.31)) / 2) < 1e-12
    assert s["priced_records"] == 3 and s["brier_deribit_fair"] < s["brier_polymarket_mid"]


# ------------------------------------------------------------------ recorder helpers
def test_book_levels_are_sorted_best_first_regardless_of_arrival_order():
    bids = [{"price": "0.10", "size": "5"}, {"price": "0.40", "size": "7"}, {"price": "0.30", "size": "0"}]
    asks = [{"price": "0.90", "size": "5"}, {"price": "0.45", "size": "9"}]
    bp, bs, ap, asz = normalize_book_levels(bids, asks)
    assert bp == [0.40, 0.10] and bs == [7.0, 5.0] and ap == [0.45, 0.90] and asz == [9.0, 5.0]


def test_crypto_question_filter():
    assert is_crypto_market_question("Will Bitcoin be above $100,000 on October 31?")
    assert is_crypto_market_question("ETH above 4k on Friday?")
    assert not is_crypto_market_question("Will the Lakers beat the Celtics?")
    assert not is_crypto_market_question("Will Solomon Islands qualify?")   # 'Sol' inside a word must not match


class _Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((table, row))


def test_recorder_writes_sorted_book_and_price_change_bbo():
    sink = _Sink()
    rec = PolymarketRecorder(sink)
    book = ('{"event_type":"book","asset_id":"T1","timestamp":"1791071949214",'
            '"bids":[{"price":"0.10","size":"5"},{"price":"0.40","size":"7"}],'
            '"asks":[{"price":"0.90","size":"5"},{"price":"0.45","size":"9"}]}')
    pc = ('{"event_type":"price_change","timestamp":"1791071950000","price_changes":['
          '{"asset_id":"T1","price":"0.41","size":"12","side":"BUY","best_bid":"0.41","best_ask":"0.45"},'
          '{"asset_id":"T1","price":"0.50","size":"3","side":"SELL","best_bid":"0.0","best_ask":"0.45"}]}')
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(rec._handle_message(book, 1_791_071_949_300_000_000, 1))
        loop.run_until_complete(rec._handle_message(pc, 1_791_071_950_100_000_000, 2))
    finally:
        loop.close()
    bbos = [r for t, r in sink.rows if t == "bbo_ticks"]
    assert bbos[0]["bid_price"] == 0.40 and bbos[0]["ask_price"] == 0.45          # from the sorted book
    assert bbos[1]["bid_price"] == 0.41 and bbos[1]["bid_size"] == 12.0           # from price_change
    assert len(bbos) == 2, "the incomplete price_change (best_bid 0.0) must not be recorded"
    depth = [r for t, r in sink.rows if t == "orderbook_l2_depth"][0]
    assert depth["bids_price"] == [0.40, 0.10] and depth["asks_price"] == [0.45, 0.90]
