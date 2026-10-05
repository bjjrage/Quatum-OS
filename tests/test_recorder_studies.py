import json
import math
import random
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from src.research.recorder_studies import run_recorder_studies, window_minutes

T0 = 1_790_000_000           # segundo de inicio (múltiplo de 60 no requerido)
T0 -= T0 % 3600
N = 6 * 3600                 # 6 horas


def _write(base, venue, table, rows, name="part.parquet"):
    d = base / venue / f"table={table}" / "year=2026"
    d.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), d / name)


def _make(base, lag=3):
    rnd = random.Random(7)
    btc = [60000.0]
    for i in range(N - 1):
        jump = rnd.choice([0.004, -0.004]) if rnd.random() < 0.002 else 0.0
        btc.append(btc[-1] * math.exp(rnd.gauss(0, 0.0002) + jump))
    alt = [10.0 * (btc[max(0, i - lag)] / btc[0]) for i in range(N)]
    rows = []
    for i in range(N):
        for sym, px in (("BTCUSDT", btc[i]), ("ALTUSDT", alt[i])):
            ts = (T0 + i) * 1_000_000_000 + 500_000_000
            rows.append({"ts_exchange_ns": ts, "ts_received_utc_ns": ts + 2_000_000_000, "symbol": sym,
                         "bid_price": px * 0.99995, "ask_price": px * 1.00005})
    _write(base, "binance_perp", "bbo_ticks", rows)
    # mercados de 15 min: Polymarket cotiza la probabilidad "vieja" (60 s de atraso) => hay ventaja
    meta, bbo = [], []
    for k in range(4, 22):
        start = T0 + k * 900
        end = start + 900
        tok_up, tok_dn = f"UP{k}", f"DN{k}"
        meta.append({"ts_polled_utc_ns": start * 10**9, "market_id": str(k), "condition_id": "c", "status": "open",
                     "question": "Bitcoin Up or Down - October 4, 3:15PM-3:30PM ET",
                     "end_date_iso": datetime.fromtimestamp(end, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                     "clob_token_ids_json": json.dumps([tok_up, tok_dn]), "outcomes_json": json.dumps(["Up", "Down"]),
                     "fee_schedule_raw_json": "", "resolution_source": "", "fee_model_version": "", "description": ""})
        for t in range(start, end, 5):
            old = max(start, t - 60) - T0
            p = 0.5 + 0.5 * math.tanh((btc[old] / btc[start - T0] - 1.0) / 0.001)
            p = min(0.97, max(0.03, p))
            bbo.append({"ts_received_utc_ns": t * 10**9 + 2_000_000_000, "symbol": tok_up,
                        "bid_price": round(p - 0.01, 3), "ask_price": round(p + 0.01, 3)})
    _write(base, "polymarket", "polymarket_metadata_history", meta)
    _write(base, "polymarket", "bbo_ticks", bbo)


def test_detects_planted_lag_and_stale_polymarket(tmp_path):
    _make(tmp_path, lag=3)
    res = run_recorder_studies(tmp_path)
    a = res["btc_vs_alts"]
    assert a["status"] == "OK" and a["eventos_btc"] > 5
    r = {x["segundos"]: x["porcentaje_del_total"] for x in a["respuesta_alts"]}
    assert r[0] < 50 and r[3] > 90                      # la alt tarda ~3 s
    op = {(x["entrar_a_los_seg"], x["mantener_seg"]): x for x in a["operaciones"]}
    assert op[(1, 10)]["neto_medio_pct"] > 0            # entrar 1 s después gana con la demora plantada
    b = res["polymarket_vs_binance"]
    assert b["status"] == "OK" and b["mercados_usados"] > 5
    assert b["error_prediccion_modelo"] < b["error_prediccion_polymarket"]   # Polymarket atrasado predice peor
    assert abs(res["desfase_reloj_pc_seg"] - 2.0) < 0.01


def test_window_parsing():
    assert window_minutes("Bitcoin Up or Down - October 4, 3:15PM-3:30PM ET") == 15
    assert window_minutes("Solana Up or Down - October 4, 11PM ET") == 60
    assert window_minutes("Ethereum Up or Down on October 4?") == 1440
