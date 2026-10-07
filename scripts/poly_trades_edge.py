"""Was there money on the table? Polymarket up/down trades that really happened vs the Binance-based model.

    uv run python scripts/poly_trades_edge.py --hours 12

No recorder, no bot: for every BTC/ETH/SOL 5m/15m up/down market that ended in the last --hours hours,
  * official result from Gamma (closed=true)
  * every taker trade from data-api.polymarket.com (time to the second, outcome, side, price)
  * Binance spot 1 s klines from data-api.binance.vision (public mirror; api.binance.com geo-blocks some servers)
Each trade is turned into "bought outcome O at price q" (selling O at p == buying the other at 1-p). The model
P(up) = Phi(ln(S_t/S_0) / (sigma*sqrt(tau))) uses Binance up to the second BEFORE the trade, sigma = std of 1 s log
returns over the previous 30 min. edge = P(O) - q. Profit per share = win - q - taker fee (rate 0.07, exponent 1).
If trades bought with edge >= 5 pts make money after fees, the lag existed and someone captured it.
"""
import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GAMMA = "https://gamma-api.polymarket.com/markets"
TRADES = "https://data-api.polymarket.com/trades"
KLINES = "https://data-api.binance.vision/api/v3/klines"
COINS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}
DUR = {5: 300, 15: 900}


def get(url, params, tries=4):
    u = url + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "quant-os"}), timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1 + 2 * i)


def binance_seconds(symbol, t0, t1):
    out = {}
    t = t0
    while t < t1:
        rows = get(KLINES, {"symbol": symbol, "interval": "1s", "startTime": t * 1000, "limit": 1000})
        if not rows:
            break
        for r in rows:
            out[int(r[0] // 1000)] = float(r[4])          # close of that second
        t = int(rows[-1][0] // 1000) + 1
    return out


def price_at(px, s, back=5):
    for k in range(back + 1):
        if s - k in px:
            return px[s - k]
    return None


def sigma(px, s, window=1800):
    rets, prev = [], None
    for k in range(s - window, s):
        v = px.get(k)
        if v and prev:
            rets.append(math.log(v / prev))
        prev = v or prev
    if len(rets) < window * 0.8:
        return None
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def fee(q, rate=0.07, exp=1.0):
    return q * rate * (q * (1 - q)) ** exp


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12)
    ap.add_argument("--lag", type=int, default=1, help="usar Binance de N segundos ANTES del trade (el timestamp "
                    "del trade es la confirmación en cadena, puede llegar segundos después del cruce)")
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_trades_edge.md"))
    a = ap.parse_args()
    now = int(time.time())
    t_lo = now - int(a.hours * 3600)
    markets = []
    for coin in COINS:
        for mins, d in DUR.items():
            s = (t_lo // d + 1) * d
            while s + d <= now - 120:
                markets.append((coin, mins, s))
                s += d
    print(f"{len(markets)} mercados; bajando Binance 1 s…", flush=True)
    px = {c: binance_seconds(sym, t_lo - 1900, now) for c, sym in COINS.items()}
    rows = []
    sig_cache = {}
    for i, (coin, mins, s) in enumerate(markets):
        slug = f"{coin}-updown-{mins}m-{s}"
        m = get(GAMMA, {"slug": slug, "closed": "true"})
        if not m:
            continue
        m = m[0]
        try:
            prices = [float(x) for x in json.loads(m["outcomePrices"])]
            outs = [str(o).lower() for o in json.loads(m["outcomes"])]
        except Exception:
            continue
        if max(prices) < 0.99:
            continue
        up_won = prices[outs.index("up")] >= 0.99
        fs = m.get("feeSchedule") or {}
        rate, exp = float(fs.get("rate", 0.07)), float(fs.get("exponent", 1))
        trades, off = [], 0
        while True:
            page = get(TRADES, {"market": m["conditionId"], "limit": 500, "offset": off})
            trades += page or []
            if not page or len(page) < 500 or off >= 3000:
                break
            off += 500
        p = px[coin]
        s0 = price_at(p, s)
        if s0 is None:
            continue
        if (coin, s) not in sig_cache:
            sig_cache[(coin, s)] = sigma(p, s)
        sg = sig_cache[(coin, s)]
        if not sg:
            continue
        for tr in trades:
            t = int(tr["timestamp"])
            tau = s + DUR[mins] - (t - a.lag)
            if t < s + 10 or tau < 5:
                continue
            st = price_at(p, t - a.lag)
            if st is None:
                continue
            pu = phi(math.log(st / s0) / (sg * math.sqrt(tau)))
            o_up = str(tr["outcome"]).lower() == "up"
            q = float(tr["price"])
            if tr["side"] == "SELL":                       # selling O at q == buying the other side at 1-q
                o_up, q = not o_up, 1 - q
            if not 0.01 <= q <= 0.99:
                continue
            p_o = pu if o_up else 1 - pu
            win = 1.0 if o_up == up_won else 0.0
            sh = float(tr["size"])
            rows.append({"slug": slug, "coin": coin, "min": mins, "start": s, "t": t, "q": q, "edge": p_o - q,
                         "profit": win - q - fee(q, rate, exp), "usd": sh * q, "shares": sh, "tau": tau})
        if i % 50 == 0:
            print(f"  {i}/{len(markets)} mercados, {len(rows)} trades", flush=True)

    def block(name, rs):
        if not rs:
            return f"| {name} | 0 | | | | | |"
        usd = sum(r["usd"] for r in rs)
        pnl = sum(r["profit"] * r["shares"] for r in rs)
        per_mkt = defaultdict(float)
        for r in rs:
            per_mkt[(r["start"], r["min"])] += r["profit"] * r["shares"]
        return (f"| {name} | {len(rs):,} | US$ {usd:,.0f} | US$ {pnl:+,.0f} | {pnl / usd * 100:+.1f}% | "
                f"{tstat([r['profit'] for r in rs]):.1f} | {tstat(list(per_mkt.values())):.1f} ({len(per_mkt)}) |")

    head = "| grupo | trades | volumen | PnL (después de fee) | por US$ | t por trade | t por ventana (n) |"
    sep = "|---|---|---|---|---|---|---|"
    out = [f"# ¿Hubo plata sobre la mesa? Trades reales de Polymarket vs modelo Binance", "",
           f"Binance tomado {a.lag} s antes del timestamp del trade. Últimas {a.hours:g} h hasta {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}. "
           f"{len(rows):,} trades tomadores en {len({r['slug'] for r in rows})} mercados resueltos.", "",
           head, sep, block("todos", rows)]
    for lo, hi in ((-1, -0.10), (-0.10, -0.05), (-0.05, 0), (0, 0.03), (0.03, 0.05), (0.05, 0.10), (0.10, 1)):
        out.append(block(f"ventaja {lo * 100:+.0f} a {hi * 100:+.0f} pts", [r for r in rows if lo <= r["edge"] < hi]))
    big = [r for r in rows if r["edge"] >= 0.05]
    out += ["", "## Ventaja ≥ 5 pts (la regla del bot), desglose", "", head, sep]
    for mins in (5, 15):
        out.append(block(f"{mins} min", [r for r in big if r["min"] == mins]))
    for c in COINS:
        out.append(block(c.upper(), [r for r in big if r["coin"] == c]))
    for name, f in (("tamaño < US$ 50", lambda r: r["usd"] < 50), ("tamaño ≥ US$ 50", lambda r: r["usd"] >= 50),
                    ("quedan > 2 min", lambda r: r["tau"] > 120), ("quedan ≤ 2 min", lambda r: r["tau"] <= 120)):
        out.append(block(name, [r for r in big if f(r)]))
    half = sorted(r["t"] for r in rows)[len(rows) // 2] if rows else 0
    out.append(block("primera mitad", [r for r in big if r["t"] < half]))
    out.append(block("segunda mitad", [r for r in big if r["t"] >= half]))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
