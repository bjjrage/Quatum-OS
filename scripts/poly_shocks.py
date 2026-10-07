"""Strange moves before the event: when a Polymarket long-dated market jumps suddenly, is the jump right (follow it) or
an overreaction (fade it)? Tested on resolved markets, entering AFTER the jump like a real follower.

    uv run python scripts/poly_shocks.py --markets 500 --days 42

Resolved binary markets (Gamma closed=true, highest volume first, short crypto up/down excluded). Hourly price of the
first outcome from clob /prices-history over the last --days days before the close (14-day chunks, the API limit).
A shock = the price moves >= --move (absolute) within 3 h, starting between 0.05 and 0.95, more than 24 h before the end
(so it is not the resolution itself), at most one shock per market per 24 h. We act --delay hours after the shock ends:
  follow = buy the side the price moved toward, at the price then; fade = buy the other side.
Edge = win - price paid (fair bet = 0). t-stat over markets (shocks in the same market are not independent).
Also: "quiet" shocks (the 48 h before were calm, < 3 pts range), the most suspicious kind (no public news build-up).
"""
import argparse
import json
import math
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from poly_trades_edge import get

GAMMA = "https://gamma-api.polymarket.com/markets"
HIST = "https://clob.polymarket.com/prices-history"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ts(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def history(token, end, days):
    out = {}
    e = int(end)
    for _ in range(math.ceil(days / 14)):
        s = e - 14 * 86400
        try:
            h = get(HIST, {"market": token, "startTs": s, "endTs": e, "fidelity": 60}).get("history", [])
        except Exception:
            h = []
        for x in h:
            out[int(x["t"]) // 3600 * 3600] = float(x["p"])
        e = s
    return out


def tstat_cluster(items):
    g = defaultdict(list)
    for c, v in items:
        g[c].append(v)
    x = [sum(v) / len(v) for v in g.values()]
    n = len(x)
    if n < 3:
        return float("nan"), n
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return (m / (sd / math.sqrt(n)) if sd > 0 else float("nan")), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", type=int, default=500)
    ap.add_argument("--days", type=int, default=42)
    ap.add_argument("--move", type=float, default=0.15)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_shocks.md"))
    a = ap.parse_args()
    mk, seen = [], set()
    # Gamma refuses large offsets (422): page through several orderings and de-duplicate
    passes = [{"order": "volumeNum", "ascending": "false"},
              {"order": "endDate", "ascending": "false", "volume_num_min": 50000},
              {"order": "endDate", "ascending": "true", "volume_num_min": 50000},
              {"order": "liquidityNum", "ascending": "false"}]
    pages = []
    for ps in passes:
        off = 0
        while off < 10000:
            try:
                page = get(GAMMA, {"closed": "true", "limit": 100, "offset": off, **ps})
            except Exception:
                break
            if not page:
                break
            pages.append(page)
            off += 100
    for page in pages:
        if len(mk) >= a.markets:
            break
        for m in page:
            slug = m.get("slug") or ""
            if "updown" in slug or "up-or-down" in slug:
                continue
            try:
                pr = [float(x) for x in json.loads(m["outcomePrices"])]
                toks = json.loads(m["clobTokenIds"])
            except Exception:
                continue
            end = ts(m.get("closedTime") or m.get("endDate"))
            if len(pr) != 2 or max(pr) < 0.99 or not end or end > time.time():
                continue
            if toks[0] in seen:
                continue
            seen.add(toks[0])
            mk.append((m.get("question", "")[:80], toks[0], pr[0] >= 0.99, end))
    mk = mk[:a.markets]
    print(f"{len(mk)} mercados; bajando precios por hora…", flush=True)
    with ThreadPoolExecutor(8) as ex:
        hists = list(ex.map(lambda m: history(m[1], m[3], a.days), mk))
    shocks = []
    for (q, _, yes_won, end), h in zip(mk, hists):
        hs = sorted(h)
        last = -1e18
        for t in hs:
            if t - last < 86400 or end - t < 86400:
                continue
            p0, p1 = h.get(t - 3 * 3600), h.get(t)
            if p0 is None or p1 is None or not 0.05 <= p0 <= 0.95 or abs(p1 - p0) < a.move:
                continue
            prev = [h[x] for x in range(t - 51 * 3600, t - 3 * 3600 + 1, 3600) if x in h]
            quiet = len(prev) >= 36 and max(prev) - min(prev) < 0.03
            up = p1 > p0
            row = {"q": q, "t": t, "p0": p0, "p1": p1, "up": up, "quiet": quiet, "win_yes": yes_won,
                   "left_d": (end - t) / 86400}
            for d in (1, 6, 24):
                pe = h.get(t + d * 3600)
                if pe is not None and 0.01 <= pe <= 0.99:
                    row[f"follow{d}"] = ((1.0 if yes_won else 0.0) - pe) if up else ((0.0 if yes_won else 1.0) - (1 - pe))
            shocks.append(row)
            last = t

    def line(name, sel, d):
        e = [(s["q"], s[f"follow{d}"]) for s in sel if f"follow{d}" in s]
        if len(e) < 15:
            return f"| {name} | {d} h | {len(e)} | | | |"
        t, n = tstat_cluster(e)
        m = sum(v for _, v in e) / len(e)
        return (f"| {name} | {d} h | {len(e)} ({n} merc.) | {m * 100:+.1f} pts (t {t:.1f}) | "
                f"{-m * 100:+.1f} pts | {sum(v > 0 for _, v in e) / len(e) * 100:.0f}% |")
    out = ["# Movimientos raros antes del evento en Polymarket: ¿seguirlos o ir en contra?", "",
           f"{len(mk)} mercados resueltos de más volumen, últimos {a.days} días antes del cierre, precio por hora. "
           f"Shocks de ≥ {a.move * 100:.0f} pts en 3 h (> 24 h antes del final): {len(shocks)}.", "",
           "| grupo | entro después de | shocks | seguir el movimiento (gana − precio) | ir en contra | aciertos siguiendo |",
           "|---|---|---|---|---|---|"]
    groups = {"todos": shocks, "subas": [s for s in shocks if s["up"]], "bajas": [s for s in shocks if not s["up"]],
              "tras 48 h quietas (sospechoso)": [s for s in shocks if s["quiet"]],
              "hacia el lado improbable (p1 < 0.5 subiendo o > 0.5 bajando)":
                  [s for s in shocks if (s["up"] and s["p1"] < 0.5) or (not s["up"] and s["p1"] > 0.5)],
              "grandes (≥ 25 pts)": [s for s in shocks if abs(s["p1"] - s["p0"]) >= 0.25],
              "faltan > 7 días": [s for s in shocks if s["left_d"] > 7]}
    for name, sel in groups.items():
        for d in (1, 6, 24):
            out.append(line(name, sel, d))
    out += ["", "Ejemplos de shocks 'tras 48 h quietas':", ""]
    for s in [s for s in shocks if s["quiet"]][:15]:
        out.append(f"- {datetime.fromtimestamp(s["t"], timezone.utc):%Y-%m-%d %H:%M} · {s['q']} · {s['p0']:.2f} → {s['p1']:.2f} · "
                   f"ganó {'Sí' if s['win_yes'] else 'No'} · faltaban {s['left_d']:.0f} d")
    out += ["", "Seguir = comprar el lado hacia donde se movió, al precio 1/6/24 h después. 0 = apuesta justa. "
            "Varios grupos y plazos probados: un t ≈ 2 aislado puede ser azar."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
