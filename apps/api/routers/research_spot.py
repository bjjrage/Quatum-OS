"""Datos diarios de Binance spot para comparaciones de ciclo (lectura pública, sin claves)."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/research", tags=["Research"])
SPOT = "https://api.binance.com"


def _ms(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def summarize_daily(rows: List[list], start_ms: int, end_ms: int) -> Dict[str, Any]:
    """rows = Binance klines 1d. Cierre en la fecha inicial/final (o la primera/última vela disponible) y máximo
    intermedio con su fecha."""
    rows = [r for r in rows if start_ms <= int(r[0]) <= end_ms]
    if not rows:
        return {"status": "SIN_DATOS"}
    iso = lambda ms: datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()
    first, last = rows[0], rows[-1]
    peak = max(rows, key=lambda r: float(r[2]))
    low = min(rows, key=lambda r: float(r[3]))
    after = [r for r in rows if int(r[0]) >= int(low[0])]
    peak_after_low = max(after, key=lambda r: float(r[2]))
    return {"low_day": iso(low[0]), "low": float(low[3]),
            "peak_after_low_day": iso(peak_after_low[0]), "peak_after_low": float(peak_after_low[2]),
            "x_low_to_peak": float(peak_after_low[2]) / float(low[3]) if float(low[3]) > 0 else None,
            "x_low_to_end": float(last[4]) / float(low[3]) if float(low[3]) > 0 else None,"status": "OK", "first_day": iso(first[0]), "first_close": float(first[4]),
            "last_day": iso(last[0]), "last_close": float(last[4]),
            "peak_day": iso(peak[0]), "peak_high": float(peak[2]),
            "x_to_end": float(last[4]) / float(first[4]), "x_to_peak": float(peak[2]) / float(first[4])}


@router.get("/spot_daily")
def spot_daily(request: Request, symbols: str, start: str, end: str):
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")
    import httpx
    s_ms, e_ms = _ms(start), _ms(end)
    out: Dict[str, Any] = {}
    with httpx.Client(timeout=30.0) as c:
        for sym in [x.strip().upper() for x in symbols.split(",") if x.strip()][:80]:
            rows, t = [], s_ms
            try:
                for _ in range(10):
                    r = c.get(f"{SPOT}/api/v3/klines", params={"symbol": sym, "interval": "1d", "startTime": t,
                                                                "endTime": e_ms, "limit": 1000})
                    if r.status_code != 200:
                        break
                    b = r.json()
                    if not b:
                        break
                    rows += b
                    if len(b) < 1000:
                        break
                    t = int(b[-1][0]) + 86_400_000
                out[sym] = summarize_daily(rows, s_ms, e_ms) if rows else {"status": "NO_EXISTE_O_SIN_DATOS"}
            except Exception as ex:
                out[sym] = {"status": "ERROR", "error": f"{type(ex).__name__}: {ex}"}
    return out


@router.get("/pumpfun_probe")
async def pumpfun_probe(request: Request, seconds: float = 20.0, source: str = "public"):
    """Prueba de 20 s contra pump.fun en vivo: cuenta transacciones y eventos decodificados y muestra ejemplos.
    No guarda nada. source=public (gratis) o helius (usa .env (HELIUS_API_KEY))."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")
    import asyncio, json, time
    import websockets
    from src.collectors.pumpfun_recorder import PUMP_PROGRAM, PumpfunRecorder, resolve_url

    class _Mem:
        def __init__(self):
            self.rows = []

        async def append(self, venue, table, row):
            self.rows.append((table, row))

    url, used = resolve_url({"source": source})
    rec = PumpfunRecorder(_Mem())
    tx = nbytes = 0
    t0 = time.time()
    err = None
    try:
        async with websockets.connect(url, open_timeout=20, ping_timeout=60, max_size=8 * 2**20) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                                      "params": [{"mentions": [PUMP_PROGRAM]}, {"commitment": "confirmed"}]}))
            while time.time() - t0 < min(seconds, 60):
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                nbytes += len(m)
                if await rec.handle_message(m) or '"logsNotification"' in m:
                    tx += 1
    except Exception as ex:
        err = f"{type(ex).__name__}: {str(ex)[:200]}"
    dt = max(time.time() - t0, 1e-9)
    samples = {}
    for table, row in rec.sink.rows:
        samples.setdefault(table, [])
        if len(samples[table]) < 2:
            samples[table].append(row)
    return {"fuente": used, "segundos": round(dt, 1), "transacciones": tx, "eventos": rec.events,
            "mb": round(nbytes / 1e6, 2), "mb_por_dia_estimado": round(nbytes / 1e6 / dt * 86400),
            "error": err, "ejemplos": samples}


@router.get("/secrets_check")
async def secrets_check(request: Request):
    """Dice si las claves están y si xAI la acepta. Nunca devuelve la clave."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")
    import httpx
    from src.common.secret_loader import describe, get_secret
    xai = get_secret("XAI_API_KEY")
    out = {"XAI_API_KEY": describe(xai), "HELIUS_API_KEY": describe(get_secret("HELIUS_API_KEY"))}
    if xai:
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {xai}"})
            out["XAI_API_KEY"]["xai_responde"] = r.status_code
            if r.status_code == 200:
                out["XAI_API_KEY"]["modelos"] = [m.get("id") for m in (r.json().get("data") or [])][:30]
        except Exception as ex:
            out["XAI_API_KEY"]["xai_error"] = type(ex).__name__
    return out


@router.get("/x_probe")
async def x_probe(request: Request, mint: str, symbol: str = "", name: str = ""):
    """UNA consulta real a X (Grok x_search) para un token. Cuesta ~US$0,1-0,3. Devuelve la fila y el uso informado."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")
    import aiohttp, time
    from src.collectors.x_watcher import TokenActivity, XWatcher, XAI_URL
    from src.common.secret_loader import get_secret

    class _Mem:
        def __init__(self):
            self.rows = []

        async def append(self, venue, table, row):
            self.rows.append(row)

    act = TokenActivity()
    act.on_create({"mint": mint, "symbol": symbol, "name": name}, time.time() - 600)
    captured = {}

    class _Spy:
        def __init__(self, s):
            self.s = s

        def post(self, *a, **k):
            cm = self.s.post(*a, **k)

            class _W:
                async def __aenter__(_):
                    r = await cm.__aenter__()
                    orig = r.json

                    async def j(content_type=None):
                        d = await orig(content_type=content_type)
                        captured["usage"] = d.get("usage")
                        captured["keys"] = list(d.keys())
                        return d
                    r.json = j
                    return r

                async def __aexit__(_, *e):
                    return await cm.__aexit__(*e)
            return _W()

    async with aiohttp.ClientSession() as s:
        xw = XWatcher(_Mem(), act, get_secret("XAI_API_KEY"), http=_Spy(s))
        row = await xw.ask(mint, time.time())
    return {"fila": row, "uso_informado": captured.get("usage"), "claves_respuesta": captured.get("keys")}


@router.get("/paper_flujo")
def paper_flujo_status():
    """Estado del paper trading del flujo comprador V1 (lee data/paper/flujo_v1/state.json)."""
    from src.paper.flujo_paper import STATE_DIR, PaperBook
    if not (STATE_DIR / "state.json").exists():
        return {"estado": "SIN_ARRANCAR"}
    b = PaperBook(STATE_DIR)
    last = b.s["rebalanceos"][-1] if b.s["rebalanceos"] else None
    pos = b.s["posiciones"]
    return {"estado": "CORRIENDO", "resumen": b.summary(), "ultimo_rebalanceo": {k: v for k, v in (last or {}).items()
            if k not in ("pesos", "senal", "libro_al_entrar")} if last else None,
            "largos": sorted(s for s, q in pos.items() if q > 0), "cortos": sorted(s for s, q in pos.items() if q < 0),
            "equity_diaria": b.s["equity_diaria"][-60:]}


async def _live_prices(symbols):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://fapi.binance.com/fapi/v1/ticker/price")
            if r.status_code == 200:
                return {d["symbol"]: float(d["price"]) for d in r.json() if d.get("symbol") in symbols}
    except Exception:
        pass
    return {}


@router.get("/paper_cuentas")
async def paper_cuentas():
    """Comparación de todas las cuentas de paper, valuadas con precios de ahora."""
    from src.paper.flujo_paper import PAPER_ROOT, STRATEGIES, PaperBook, exam_view
    books = {n: PaperBook(PAPER_ROOT / n) for n in STRATEGIES if (PAPER_ROOT / n / "state.json").exists()}
    syms = {s_ for b in books.values() for s_ in b.s["posiciones"]}
    prices = await _live_prices(syms)
    out = []
    for n, b in books.items():
        ok = all(s_ in prices for s_ in b.s["posiciones"])
        eq = b.equity(prices) if ok else None
        c0 = b.s["capital_inicial"]
        out.append({"cuenta": n, "descripcion": STRATEGIES[n][0], "equity": eq,
                    "ganancia_pct": ((eq / c0 - 1) * 100) if eq else None,
                    "posiciones": len(b.s["posiciones"]), "rebalanceos": len(b.s["rebalanceos"]),
                    "costos_y_funding": b.s["costos_pagados"] + b.s["funding_pagado"], "desde": b.s["creado"],
                    "capital_inicial": c0, "examen": exam_view(b, eq)})
    return {"cuentas": out}


@router.get("/paper_flujo_live")
async def paper_flujo_live(cuenta: str = "flujo_v1"):
    """Posiciones de una cuenta de paper valuadas con precios de Binance en este momento."""
    from datetime import datetime, timedelta, timezone
    from src.paper.flujo_paper import PAPER_ROOT, STRATEGIES, PaperBook, exam_view
    if cuenta not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Cuenta desconocida")
    REB_DAYS = STRATEGIES[cuenta][1]
    if not (PAPER_ROOT / cuenta / "state.json").exists():
        return {"estado": "SIN_ARRANCAR", "cuenta": cuenta}
    b = PaperBook(PAPER_ROOT / cuenta)
    pos = b.s["posiciones"]
    prices = await _live_prices(set(pos))
    ent = b.entry_prices()
    rows = []
    for sym, q in pos.items():
        px, e = prices.get(sym), ent.get(sym)
        pnl = q * (px - e) if (px and e) else None
        rows.append({"symbol": sym, "lado": "COMPRA" if q > 0 else "VENTA", "cantidad": q, "entrada": e, "precio": px,
                     "valor_usd": abs(q) * px if px else None, "ganancia_usd": pnl,
                     "ganancia_pct": (pnl / (abs(q) * e) * 100) if (pnl is not None and e) else None})
    rows.sort(key=lambda x: -(x["ganancia_usd"] or 0))
    eq = b.equity(prices) if len(prices) == len(pos) else None
    hist = b.s["equity_diaria"]
    ayer = hist[-2]["equity"] if len(hist) >= 2 else b.s["capital_inicial"]
    last_ms = b.s["ultimo_rebalanceo_ms"]
    nxt = None
    if last_ms:                                    # misma regla que el bot: >= 7 días - 1 h y entre 00:05 y 00:59 UTC
        earliest = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc) + timedelta(days=REB_DAYS, hours=-1)
        day0 = earliest.replace(hour=0, minute=5, second=0, microsecond=0)
        if earliest <= day0:
            nxt = day0
        elif earliest.hour == 0:
            nxt = earliest
        else:
            nxt = day0 + timedelta(days=1)
    return {"estado": "CORRIENDO", "cuenta": cuenta, "descripcion": STRATEGIES[cuenta][0],
            "hora": datetime.now(timezone.utc).isoformat(), "equity": eq,
            "capital_inicial": b.s["capital_inicial"], "apalancamiento": b.s["apalancamiento"],
            "ganancia_total_usd": (eq - b.s["capital_inicial"]) if eq else None,
            "ganancia_total_pct": ((eq / b.s["capital_inicial"] - 1) * 100) if eq else None,
            "ganancia_hoy_usd": (eq - ayer) if eq else None, "costos_pagados": b.s["costos_pagados"],
            "funding_pagado": b.s["funding_pagado"], "proximo_rebalanceo": nxt.isoformat() if nxt else None,
            "rebalanceos": len(b.s["rebalanceos"]), "posiciones": rows, "equity_diaria": hist[-90:],
            "desde": b.s["creado"], "examen": exam_view(b, eq)}


@router.get("/pump_paper")
def pump_paper_status():
    """Cuentas de paper de pump.fun (grupos + nichos) leídas de data/paper/pump_*/state.json."""
    import json as _json
    from src.paper.pump_paper import ACCOUNTS, PAPER_ROOT
    out = []
    extra: Dict[str, Any] = {}
    for name in ACCOUNTS:
        p = PAPER_ROOT / f"pump_{name}" / "state.json"
        if not p.exists():
            continue
        try:
            s = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        c0 = s.get("capital_inicial", 10.0)
        eq = s.get("equity", s.get("cash", c0))
        n = s.get("n_cerradas", 0)
        out.append({"cuenta": name, "descripcion": s.get("descripcion", ""), "equity_sol": eq,
                    "resultado_pct": (eq / c0 - 1) * 100 if c0 else None, "abiertas": len(s.get("posiciones", {})),
                    "cerradas": n, "aciertos_pct": (s.get("ganadas", 0) / n * 100) if n else None,
                    "resultado_cerradas_sol": s.get("resultado_sol", 0.0), "comisiones_sol": s.get("comisiones_sol", 0.0),
                    "senales": s.get("senales", 0), "saltadas": s.get("saltadas", 0), "tomas_2x": s.get("tomas_2x", 0),
                    "ultimas_cerradas": (s.get("cerradas") or [])[-8:][::-1], "actualizado": s.get("actualizado")})
        extra = {"grupos": s.get("grupos"), "billeteras_en_grupos": s.get("billeteras_en_grupos"),
                 "ultimas_senales": (s.get("ultimas_senales") or [])[::-1], "nichos_ahora": s.get("nichos_ahora") or []}
    return {"cuentas": out, **extra}


@router.get("/lider_paper")
def lider_paper_status():
    """Paper "líder explotó -> rezagadas + X": cuentas, medida de exceso vs mercado, eventos y gasto de X."""
    import json as _json
    from src.paper.lider_paper import LIDER_ACCOUNTS, PAPER_ROOT
    cuentas = []
    for name, desc in LIDER_ACCOUNTS.items():
        p = PAPER_ROOT / name / "state.json"
        if not p.exists():
            continue
        try:
            s = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        hist = s.get("equity_diaria") or []
        c0 = s.get("capital_inicial", 10000.0)
        eq = hist[-1]["equity"] if hist else s.get("cash", c0)
        cl = s.get("cerrados") or []
        ex = [c["exceso_vs_mercado"] for c in cl if c.get("exceso_vs_mercado") is not None]
        cuentas.append({"cuenta": name, "descripcion": desc, "equity": eq, "resultado_pct": (eq / c0 - 1) * 100,
                        "abiertas": len(s.get("lotes") or []), "cerradas": len(cl),
                        "exceso_medio_pct": (sum(ex) / len(ex) * 100) if ex else None,
                        "aciertos_pct": (sum(1 for c in cl if c["ret_neto"] > 0) / len(cl) * 100) if cl else None,
                        "costos": s.get("costos_pagados", 0.0), "funding": s.get("funding_pagado", 0.0)})
    ev: Dict[str, Any] = {}
    f = PAPER_ROOT / "lider_eventos.json"
    if f.exists():
        try:
            ev = _json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            ev = {}
    eventos = []
    for e in (ev.get("eventos") or [])[-15:][::-1]:
        eventos.append({"dia": e.get("dia"), "segmento": e.get("segmento"), "lideres": e.get("lideres"),
                        "rezagadas": [{"symbol": r["symbol"], "r3": r["r3"], "x": r.get("x")} for r in e.get("rezagadas", [])],
                        "abrio": e.get("abrio")})
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gasto = ev.get("gasto_x") or {}
    return {"cuentas": cuentas, "eventos": eventos, "ultimo_chequeo": ev.get("ultimo_chequeo_dia"),
            "gasto_x_hoy": gasto.get(hoy, 0.0), "gasto_x_total": sum(gasto.values())}
