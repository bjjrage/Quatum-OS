import json
import math

from src.paper.poly_updown_paper import (Config, Market, PolyUpDownPaper, Quote, SecondMids, apply_book_event, decide,
                                         fee_per_share, market_from_gamma, model_prob, official_up_won, parse_fee,
                                         settle_pnl)


def test_model_prob_and_fee():
    assert abs(model_prob(100, 100, 0.001, 60) - 0.5) < 1e-12
    assert model_prob(100, 101, 0.0005, 60) > 0.99 and model_prob(100, 99, 0.0005, 60) < 0.01
    assert math.isnan(model_prob(100, 100, 0, 60))
    assert abs(fee_per_share(0.4, (0.07, 1)) - 0.4 * 0.07 * 0.24) < 1e-12
    assert parse_fee('{"rate": 0.07, "exponent": 1, "takerOnly": true}') == (0.07, 1.0) and parse_fee("x") is None


def test_second_mids_sigma_needs_coverage():
    m = SecondMids()
    for s in range(1000):
        m.set(s, 100 * math.exp(0.001 * (1 if s % 2 else -1) * (s % 2)))
    assert m.sigma(999, 900, 0.8) > 0 and math.isnan(m.sigma(999, 1800, 0.8))
    assert m.at(1005, max_gap=10) == m.mids[999] and math.isnan(m.at(5000, max_gap=10))


def test_decide_sides():
    up, down = Quote(bid=0.38, bid_size=50, ask=0.40, ask_size=30), Quote(bid=0.58, ask=0.60, ask_size=20)
    assert decide(0.50, up, down, 0.05) == ("up", 0.40, 30)
    assert decide(0.30, up, down, 0.05) == ("down", 0.60, 20)
    assert decide(0.42, up, down, 0.05) is None
    assert decide(0.30, up, None, 0.05) == ("down", 1 - 0.38, 50)       # no Down book: via Up's bid
    assert decide(float("nan"), up, down, 0.05) is None


def test_book_events_unsorted_levels_and_price_change():
    q = {}
    apply_book_event(q, {"event_type": "book", "asset_id": "T", "bids": [{"price": "0.30", "size": "5"}, {"price": "0.38", "size": "9"}],
                         "asks": [{"price": "0.55", "size": "1"}, {"price": "0.41", "size": "7"}]}, 1.0)
    assert (q["T"].bid, q["T"].bid_size, q["T"].ask, q["T"].ask_size) == (0.38, 9, 0.41, 7)
    apply_book_event(q, {"event_type": "price_change", "price_changes": [
        {"asset_id": "T", "price": "0.40", "size": "12", "side": "SELL", "best_bid": "0.38", "best_ask": "0.40"}]}, 2.0)
    assert (q["T"].ask, q["T"].ask_size, q["T"].bid_size) == (0.40, 12, 9)


def test_gamma_parsing_and_official_resolution():
    it = {"slug": "btc-updown-5m-1000", "clobTokenIds": json.dumps(["D", "U"]), "outcomes": json.dumps(["Down", "Up"]),
          "feeSchedule": {"rate": 0.07, "exponent": 1}}
    mk = market_from_gamma(it, "btc", "5m", 1000)
    assert (mk.up_token, mk.down_token, mk.end_s, mk.asset, mk.fee) == ("U", "D", 1300, "BTCUSDT", (0.07, 1.0))
    assert official_up_won({**it, "closed": True, "outcomePrices": json.dumps(["0", "1"])}) is True
    assert official_up_won({**it, "closed": False}) is None


def test_engine_end_to_end_signal_fill_settle_resolve(tmp_path):
    eng = PolyUpDownPaper(Config(threshold=0.05, delay_s=2, max_usd=25, vol_window_s=600), tmp_path)
    t0 = 1_000_000
    mk = Market("btc-updown-5m-x", "BTCUSDT", 5, t0, t0 + 300, "U", "D", fee=(0.07, 1.0))
    eng.markets[mk.slug] = mk
    price = 100.0
    for s in range(t0 - 700, t0 + 310):
        price *= math.exp(0.0002 if s % 2 else -0.0002)            # some volatility
        if s >= t0 + 100:
            price *= 1.0003                                       # BTC rises during the market
        eng.on_binance("BTCUSDT", price - 0.01, price + 0.01, s)
        eng.quotes["U"] = Quote(bid=0.48, bid_size=100, ask=0.50, ask_size=40, ts=s)   # stale Polymarket book
        eng.quotes["D"] = Quote(bid=0.48, bid_size=100, ask=0.52, ask_size=40, ts=s)
        eng.tick(s + 0.5)
    events = [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    kinds = [e["kind"] for e in events]
    assert kinds[:3] == ["signal", "fill", "settle"]
    fill = events[1]
    assert fill["side"] == "up" and fill["price"] == 0.50 and abs(fill["usd"] - 20) < 1e-9   # 40 shares * 0.50 < US$25 cap
    settle = events[2]
    assert settle["up_won_binance"] is True and settle["pnl"] > 0
    eng.on_official(mk, True)
    assert eng.stats["oficiales"] == 1 and eng.stats["pnl_oficial_usd"] == settle["pnl"]
    assert abs(settle_pnl({"side": "up", "price": 0.5, "shares": 40, "fee_per_share": 0.01}, False) + 40 * 0.51) < 1e-9


def test_engine_misses_when_price_moves_and_ignores_stale_binance(tmp_path):
    eng = PolyUpDownPaper(Config(threshold=0.05, delay_s=2, vol_window_s=600), tmp_path)
    t0 = 2_000_000
    mk = Market("eth-updown-5m-y", "ETHUSDT", 5, t0, t0 + 300, "U", "D")
    eng.markets[mk.slug] = mk
    price = 100.0
    for s in range(t0 - 700, t0 + 200):
        price *= math.exp(0.0002 if s % 2 else -0.0002) * (1.0003 if s >= t0 + 100 else 1)
        eng.on_binance("ETHUSDT", price - 0.01, price + 0.01, s)
        signalled = any(e for e in (tmp_path / "events.jsonl").read_text().splitlines() if '"signal"' in e) \
            if (tmp_path / "events.jsonl").exists() else False
        ask = 0.70 if signalled else 0.50                      # the stale offer disappears before our order lands
        eng.quotes["U"] = Quote(bid=0.48, bid_size=100, ask=ask, ask_size=40, ts=s)
        eng.tick(s + 0.5)
    kinds = [json.loads(x)["kind"] for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert kinds[:2] == ["signal", "miss"] and eng.stats["llenadas"] == 0
    eng.tick(t0 + 10_000)                                       # Binance silent for hours: no fake mids written
    assert t0 + 10_000 not in eng.mids["ETHUSDT"].mids
