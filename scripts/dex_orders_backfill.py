"""Rebuild the history of PAID promotions (DexScreener) for the pump.fun tokens we recorded.

    uv run --with duckdb python scripts/dex_orders_backfill.py --data data/raw            # runs for hours, resumable
    uv run --with duckdb python scripts/dex_orders_backfill.py --data data/raw --limit 50 # quick test

DexScreener answers GET https://api.dexscreener.com/orders/v1/solana/{mint} with the paid orders of a token and the
exact payment time:
  {"orders": [{"type": "tokenProfile", "status": "approved", "paymentTimestamp": <ms>}, ...], "boosts": [...]}
so we can recover promotions that happened BEFORE our watcher was running, which multiplies the sample of the paid-push
study. Candidates = pump.fun tokens with >= --min-buyers distinct buyers in their first 10 minutes (promoted tokens
have traction). One row per token is appended to data/research/dex_orders.jsonl ({"mint", "queried_utc", "orders",
"boosts"}); tokens already in the file are skipped, so it can be stopped and restarted any time.
Rate limit: DexScreener allows 60 requests/minute on this endpoint; default --rpm 50.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from recordings_summary import is_valid_parquet  # noqa: E402

URL = "https://api.dexscreener.com/orders/v1/solana/{mint}"


def src(root: Path, table: str):
    d = root / "pumpfun" / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def candidates(data: Path, min_buyers: int):
    trs, crs = src(data, "pumpfun_trades"), src(data, "pumpfun_creates")
    if not trs or not crs:
        raise SystemExit("Faltan pumpfun_trades / pumpfun_creates en --data")
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.execute(f"CREATE TABLE born AS SELECT mint, MIN(ts_received_utc_ns)/1e9 AS born FROM {crs} GROUP BY 1")
    rows = con.execute(f"""SELECT b.mint FROM born b JOIN (
            SELECT t.mint, COUNT(DISTINCT t."user") AS buyers FROM {trs} t JOIN born b2 USING (mint)
            WHERE t.is_buy AND t.ts_received_utc_ns/1e9 <= b2.born + 600 GROUP BY 1) x USING (mint)
        WHERE x.buyers >= {min_buyers} ORDER BY b.born DESC""").fetchall()
    return [r[0] for r in rows]


def fetch(mint: str):
    for i in range(5):
        try:
            req = urllib.request.Request(URL.format(mint=mint), headers={"User-Agent": "quant-os"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (i + 1))
            elif e.code == 404:
                return {"orders": [], "boosts": []}
            else:
                time.sleep(2 + i)
        except Exception:
            time.sleep(2 + i)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "research" / "dex_orders.jsonl")
    ap.add_argument("--min-buyers", type=int, default=15)
    ap.add_argument("--rpm", type=float, default=50.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N queries (test)")
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if a.out.exists():
        for ln in a.out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(ln)["mint"])
            except Exception:
                pass
    todo = [m for m in candidates(a.data, a.min_buyers) if m not in done]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(todo):,} tokens por consultar ({len(done):,} ya hechos). ~{len(todo) / a.rpm / 60:.1f} h a {a.rpm:g}/min.",
          flush=True)
    gap, n, with_orders, t0 = 60.0 / a.rpm, 0, 0, time.time()
    with a.out.open("a", encoding="utf-8") as fh:
        for m in todo:
            t_req = time.time()
            r = fetch(m)
            if r is None:
                continue
            orders, boosts = r.get("orders") or [], r.get("boosts") or []
            fh.write(json.dumps({"mint": m, "queried_utc": int(time.time()), "orders": orders, "boosts": boosts}) + "\n")
            fh.flush()
            n += 1
            with_orders += bool(orders or boosts)
            if n % 200 == 0:
                print(f"  {n:,}/{len(todo):,} consultados, {with_orders} con promoción paga, "
                      f"{(time.time() - t0) / 60:.0f} min", flush=True)
            time.sleep(max(0.0, gap - (time.time() - t_req)))
    print(f"Listo: {n:,} consultados, {with_orders} con promoción paga. Archivo: {a.out}")


if __name__ == "__main__":
    main()
