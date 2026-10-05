"""Paper trading en pump.fun: detectar GRUPOS que acumulan en silencio, entrar con ellos y salir antes que ellos.

Idea (de Marcelo): el pump no aparece solo; lo arma un grupo. Primero compra callado, después lo empuja en X y al final
le vende a la gente que entra tarde. Ganarle a esa gente = entrar mientras el grupo acumula y salir cuando el grupo vende.

  * Grupos (en vivo, solo con el pasado): dos billeteras quedan "unidas" si compraron el MISMO token con <= 2 slots
    (~1 s) de diferencia en >= 3 tokens distintos, y eso es al menos el 50% de los tokens que compra la más chica de
    las dos (así no se juntan bots que compran todo). Se excluyen billeteras que compraron > 150 tokens (bots).
  * Señal "grupo acumulando": en un token de <= 30 min, >= 2 billeteras unidas entre sí compraron (en <= 10 min) y
    todavía hay < 40 billeteras distintas en el token (la gente no llegó).
  * Cuentas (10 SOL c/u; cada entrada = 5% del capital actual, así crece con interés compuesto; máx 20 abiertas):
      Salida ESCALERA (idea de Marcelo: 2x + 2x + 3x moviendo capital, no aguantar por un 10x): al 2x vende la
      mitad (recupera lo puesto); el resto corre con stop móvil 35% debajo de su máximo. Antes del 2x: stop -50% y
      salida si en 2 h no llegó. Graduación = vende todo.
      - grupo:           señal de grupo; escalera + vende todo si el grupo vendió >= 30% de lo que llegó a tener.
      - grupo_nicho:     señal de grupo Y nicho caliente; igual que "grupo".
      - nicho:           solo nicho: token de <= 30 min y < 40 billeteras en un nicho caliente (src/research/niches.py:
                         volumen de 30 min >= 2x su promedio de 6 h); escalera.
      - grupo_aguantar:  misma entrada que "grupo" pero aguanta al 10x (o -50% / 2 h): ¿escalera o aguantar?
      - detector_tarde:  entra cuando un token de < 1 h junta >= 50 compradores y >= 10 SOL netos en 5 min (el
                         detector viejo); escalera. Sirve para ver si "llegar tarde" pierde.
      - azar (control):  en el mismo momento de cada señal de grupo, otro token de <= 30 min con < 40 billeteras;
                         escalera.
  * Ejecución realista: se llena con la curva de la operación SIGUIENTE a la señal (llegamos tarde), comisión
    pump.fun 1,25% por lado, 0,0005 SOL de prioridad por envío.
  * Los tokens de señales de grupo se mandan primero al vigilante de X (dentro del tope diario) para medir después
    si el empuje en X llega después de la acumulación.
Estado en data/paper/pump_<cuenta>/state.json.
"""
from __future__ import annotations

import json
import random
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from src.common.logger import setup_logger

logger = setup_logger("pump_paper")

ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = ROOT / "data" / "paper"
LAMPORTS, TOKEN_UNITS = 1e9, 1e6
FEE, TX_SOL = 0.0125, 0.0005
IDLE_CLOSE_S = 7200
FILL_TIMEOUT_S = 15

SMART = {"min_tokens": 4, "min_pnl_sol": 1.0, "min_roi": 0.25, "min_wins": 0.40}     # solo informativo

GROUP = {"window_slots": 2, "min_shared": 3, "min_overlap": 0.5, "max_wallet_tokens": 150, "max_burst": 40}
SIGNAL = {"max_age_s": 1800, "max_crowd": 40, "within_s": 600, "min_members": 2}

# Salida "escalera" (idea de Marcelo: no aguantar por un 10x; ir sacando de a pedazos y mover el capital):
#   al 2x vende la mitad (recupera lo puesto); el resto corre con stop móvil 35% debajo de su máximo.
#   Antes del 2x: stop -50% y salida si en 2 h no llegó. Después del 2x, tope de seguridad 6 h.
LADDER = {"take_at": 1.0, "take_frac": 0.5, "trail": 0.35, "sl": -0.5, "max_wait_s": 7200, "max_hold_s": 6 * 3600}
HOLD10 = {"take_at": 9.0, "take_frac": 1.0, "trail": None, "sl": -0.5, "max_wait_s": 7200, "max_hold_s": 7200}
SIZE_FRAC, MIN_SIZE_SOL = 0.05, 0.05        # 5% del capital actual por entrada (interés compuesto)

ACCOUNTS: Dict[str, Dict[str, Any]] = {
    "grupo": {"desc": "Grupo acumulando: escalera + vende si el grupo vende", **LADDER, "group_exit": 0.30},
    "grupo_nicho": {"desc": "Grupo + nicho caliente: escalera + vende si el grupo vende", **LADDER, "group_exit": 0.30},
    "nicho": {"desc": "Solo nicho caliente (token joven): escalera", **LADDER},
    "grupo_aguantar": {"desc": "Grupo acumulando, pero AGUANTA al 10x (comparación)", **HOLD10},
    "detector_tarde": {"desc": "Detector viejo (50 compradores en 5 min): escalera", **LADDER},
    "azar": {"desc": "CONTROL: token joven al azar en el mismo momento: escalera", **LADDER},
}


# --------------------------------------------------------------------------- curva (producto constante)
def buy_tokens(sol: float, vsol: int, vtok: int) -> float:
    """Tokens (unidades crudas) que da comprar `sol` SOL (ya incluida la comisión) con reservas virtuales."""
    x = sol * (1 - FEE) * LAMPORTS
    return vtok - vsol * vtok / (vsol + x) if vsol > 0 and vtok > 0 else 0.0


def sell_sol(tok: float, vsol: int, vtok: int) -> float:
    """SOL netos (después de comisión) de vender `tok` unidades crudas."""
    if vsol <= 0 or vtok <= 0 or tok <= 0:
        return 0.0
    return (vsol - vsol * vtok / (vtok + tok)) / LAMPORTS * (1 - FEE)


def price_sol(vsol: float, vtok: float) -> float:
    return (vsol / LAMPORTS) / (vtok / TOKEN_UNITS) if vsol and vtok else 0.0


# --------------------------------------------------------------------------- ranking de billeteras
class WalletBook:
    def __init__(self):
        self.pairs: Dict[Tuple[str, str], List[float]] = {}        # (billetera, token) -> [gastado, recibido, tokens]
        self.mint_users: Dict[str, Set[str]] = {}
        self.mint_last: Dict[str, Tuple[float, float]] = {}       # token -> (último ts, último precio)
        self.stats: Dict[str, List[float]] = {}                   # billetera -> [tokens, pnl, gastado, aciertos]
        self.n_smart = 0

    def update(self, user: str, mint: str, is_buy: bool, sol: float, tok: float, px: float, ts: float) -> None:
        p = self.pairs.get((user, mint))
        if p is None:
            p = self.pairs[(user, mint)] = [0.0, 0.0, 0.0]
            self.mint_users.setdefault(mint, set()).add(user)
        if is_buy:
            p[0] += sol
            p[2] += tok
        else:
            p[1] += sol
            p[2] -= tok
        self.mint_last[mint] = (ts, px if px > 0 else self.mint_last.get(mint, (ts, 0.0))[1])

    def _add_closed(self, user: str, spent: float, recv: float, tok: float, px: float) -> None:
        if spent <= 0:
            return
        pnl = recv + max(tok, 0.0) * px - spent
        s = self.stats.setdefault(user, [0, 0.0, 0.0, 0])
        s[0] += 1
        s[1] += pnl
        s[2] += spent
        s[3] += 1 if pnl > 0 else 0

    def close_idle(self, now: float, idle_s: float = IDLE_CLOSE_S) -> int:
        n = 0
        for m in [m for m, (ts, _) in self.mint_last.items() if now - ts > idle_s]:
            px = self.mint_last.pop(m)[1]
            for u in self.mint_users.pop(m, ()):
                p = self.pairs.pop((u, m), None)
                if p:
                    self._add_closed(u, p[0], p[1], p[2], px)
            n += 1
        self.n_smart = sum(1 for u in self.stats if self.is_smart(u))
        return n

    def is_smart(self, user: str) -> bool:
        s = self.stats.get(user)
        if not s or s[0] < SMART["min_tokens"] or s[2] <= 0:
            return False
        return s[1] >= SMART["min_pnl_sol"] and s[1] / s[2] >= SMART["min_roi"] and s[3] / s[0] >= SMART["min_wins"]


# --------------------------------------------------------------------------- cuenta de paper
class PumpAccount:
    def __init__(self, name: str, rules: Dict[str, Any], root: Path = PAPER_ROOT, capital: float = 10.0,
                 max_open: int = 20):
        self.name, self.rules = name, rules
        self.path = Path(root) / f"pump_{name}" / "state.json"
        self.s: Dict[str, Any] = {"capital_inicial": capital, "cash": capital, "max_abiertas": max_open,
                                  "posiciones": {}, "cerradas": [], "n_cerradas": 0, "ganadas": 0, "resultado_sol": 0.0,
                                  "comisiones_sol": 0.0, "senales": 0, "saltadas": 0, "tomas_2x": 0,
                                  "creado": datetime.now(timezone.utc).isoformat(), "descripcion": rules["desc"]}
        if self.path.exists():
            self.s.update(json.loads(self.path.read_text(encoding="utf-8")))
        self.pending_buy: Dict[str, Dict[str, Any]] = {}
        self.pending_sell: Dict[str, Tuple[float, str, float]] = {}   # token -> (ts, motivo, fracción)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def holds(self, mint: str) -> bool:
        return mint in self.s["posiciones"] or mint in self.pending_buy

    def book_equity(self) -> float:
        return self.s["cash"] + sum(p["costo_restante"] for p in self.s["posiciones"].values())

    def entry_size(self) -> float:
        return max(MIN_SIZE_SOL, SIZE_FRAC * self.book_equity())

    def request_buy(self, mint: str, now: float, wallet: str = "", info: Optional[Dict[str, Any]] = None) -> bool:
        self.s["senales"] += 1
        size = self.entry_size()
        if self.holds(mint) or len(self.s["posiciones"]) + len(self.pending_buy) >= self.s["max_abiertas"] \
                or self.s["cash"] < size + TX_SOL:
            self.s["saltadas"] += 1
            return False
        self.pending_buy[mint] = {"ts": now, "wallet": wallet, "size": size, **(info or {})}
        return True

    def _fill_buy(self, mint: str, vsol: int, vtok: int, now: float) -> None:
        req = self.pending_buy.pop(mint)
        size = min(req["size"], self.s["cash"] - TX_SOL)
        tok = buy_tokens(size, vsol, vtok) if size > 0 else 0.0
        if tok <= 0:
            return
        self.s["cash"] -= size + TX_SOL
        self.s["comisiones_sol"] += size * FEE + TX_SOL
        cost = size + TX_SOL
        self.s["posiciones"][mint] = {"tok": tok, "costo": cost, "costo_restante": cost, "cobrado": 0.0,
                                      "max_valor": cost, "tomado": False, "entrada_ts": now,
                                      "precio_entrada": price_sol(vsol, vtok), "billetera": req.get("wallet", ""),
                                      "simbolo": req.get("symbol", ""), "demora_s": round(now - req["ts"], 1)}

    def _fill_sell(self, mint: str, vsol: int, vtok: int, now: float, reason: str, frac: float = 1.0) -> None:
        pos = self.s["posiciones"].get(mint)
        self.pending_sell.pop(mint, None)
        if not pos:
            return
        q = pos["tok"] * min(max(frac, 0.0), 1.0)
        got = max(sell_sol(q, vsol, vtok) - TX_SOL, 0.0)
        self.s["cash"] += got
        self.s["comisiones_sol"] += got * FEE / (1 - FEE) + TX_SOL
        pos["cobrado"] += got
        if frac < 0.999 and q < pos["tok"]:
            pos["costo_restante"] *= (pos["tok"] - q) / pos["tok"]
            pos["tok"] -= q
            pos["tomado"] = True
            pos["max_valor"] = 0.0                     # el stop móvil se mide sobre lo que queda
            self.s["tomas_2x"] += 1
            return
        del self.s["posiciones"][mint]
        pnl = pos["cobrado"] - pos["costo"]
        self.s["n_cerradas"] += 1
        self.s["ganadas"] += 1 if pnl > 0 else 0
        self.s["resultado_sol"] += pnl
        self.s["cerradas"] = (self.s["cerradas"] + [{"mint": mint, "simbolo": pos.get("simbolo", ""), "pnl_sol": pnl,
                              "multiplo": pos["cobrado"] / pos["costo"], "motivo": reason,
                              "tomo_2x": pos["tomado"], "minutos": round((now - pos["entrada_ts"]) / 60, 1),
                              "cerrada": datetime.fromtimestamp(now, tz=timezone.utc).isoformat()}])[-300:]

    def value(self, mint: str, vsol: int, vtok: int) -> float:
        pos = self.s["posiciones"].get(mint)
        return max(sell_sol(pos["tok"], vsol, vtok) - TX_SOL, 0.0) if pos else 0.0

    def mark_sell(self, mint: str, now: float, reason: str, frac: float = 1.0) -> None:
        cur = self.pending_sell.get(mint)
        if mint in self.s["posiciones"] and (cur is None or (frac > cur[2])):
            self.pending_sell[mint] = (now, reason, frac)

    def on_trade(self, mint: str, vsol: int, vtok: int, now: float) -> None:
        """Se llama con el estado de la curva DESPUÉS de cada operación de ese token."""
        if mint in self.pending_sell:
            _, reason, frac = self.pending_sell[mint]
            self._fill_sell(mint, vsol, vtok, now, reason, frac)
            return
        if mint in self.pending_buy:
            self._fill_buy(mint, vsol, vtok, now)
            return
        pos = self.s["posiciones"].get(mint)
        if not pos:
            return
        r = self.rules
        val = self.value(mint, vsol, vtok)
        pos["max_valor"] = max(pos["max_valor"], val)
        if not pos["tomado"]:
            ret = val / pos["costo"] - 1
            if ret >= r["take_at"]:
                self.mark_sell(mint, now, f"{1 + r['take_at']:.0f}x", r["take_frac"])
            elif ret <= r["sl"]:
                self.mark_sell(mint, now, f"stop {r['sl']:.0%}")
        elif r.get("trail") and val <= (1 - r["trail"]) * pos["max_valor"]:
            self.mark_sell(mint, now, f"stop móvil -{r['trail']:.0%} desde el máximo")

    def tick(self, now: float, curves: Dict[str, List[float]]) -> None:
        for mint, req in list(self.pending_buy.items()):
            if now - req["ts"] >= FILL_TIMEOUT_S:
                c = curves.get(mint)
                if c:
                    self._fill_buy(mint, int(c[0]), int(c[1]), now)
                else:
                    self.pending_buy.pop(mint, None)
        for mint, pos in list(self.s["posiciones"].items()):
            age = now - pos["entrada_ts"]
            if not pos["tomado"] and age >= self.rules["max_wait_s"]:
                self.mark_sell(mint, now, f"no llegó al 2x en {self.rules['max_wait_s'] // 60} min")
            elif age >= self.rules["max_hold_s"]:
                self.mark_sell(mint, now, f"tope {self.rules['max_hold_s'] // 3600} h")
        for mint, (ts, reason, frac) in list(self.pending_sell.items()):
            if now - ts >= FILL_TIMEOUT_S:
                c = curves.get(mint)
                self._fill_sell(mint, int(c[0]) if c else 0, int(c[1]) if c else 0, now, reason, frac)

    def equity(self, curves: Dict[str, List[float]]) -> float:
        return self.s["cash"] + sum(self.value(m, int(curves[m][0]), int(curves[m][1]))
                                    for m in self.s["posiciones"] if m in curves)


# --------------------------------------------------------------------------- grupos coordinados
class GroupGraph:
    """Une billeteras que compran los mismos tokens en el mismo segundo, repetidamente."""

    def __init__(self):
        self.recent: Dict[str, Deque[Tuple[int, str]]] = {}        # token -> compras recientes (slot, billetera)
        self.pair_tokens: Dict[Tuple[str, str], Set[str]] = {}
        self.wallet_tokens: Dict[str, int] = {}                    # tokens distintos que compró cada billetera
        self._wallet_seen: Set[Tuple[str, str]] = set()
        self.links: Dict[str, Set[str]] = {}                       # uniones firmes

    def on_buy(self, mint: str, user: str, slot: int) -> None:
        if (user, mint) not in self._wallet_seen:
            self._wallet_seen.add((user, mint))
            self.wallet_tokens[user] = self.wallet_tokens.get(user, 0) + 1
        dq = self.recent.setdefault(mint, deque())
        while dq and slot - dq[0][0] > GROUP["window_slots"]:
            dq.popleft()
        others = {u for _, u in dq if u != user}
        dq.append((slot, user))
        if not others or len(others) > GROUP["max_burst"]:
            return
        for o in others:
            key = (user, o) if user < o else (o, user)
            toks = self.pair_tokens.setdefault(key, set())
            if mint in toks:
                continue
            toks.add(mint)
            if len(toks) >= GROUP["min_shared"]:
                self._maybe_link(key, len(toks))

    def _maybe_link(self, key: Tuple[str, str], shared: int) -> None:
        a, b = key
        na, nb = self.wallet_tokens.get(a, 0), self.wallet_tokens.get(b, 0)
        if max(na, nb) > GROUP["max_wallet_tokens"] or shared < GROUP["min_overlap"] * min(na, nb):
            self.links.get(a, set()).discard(b)
            self.links.get(b, set()).discard(a)
            return
        self.links.setdefault(a, set()).add(b)
        self.links.setdefault(b, set()).add(a)

    def is_member(self, user: str) -> bool:
        return bool(self.links.get(user)) and self.wallet_tokens.get(user, 0) <= GROUP["max_wallet_tokens"]

    def linked(self, user: str) -> Set[str]:
        return self.links.get(user, set()) if self.is_member(user) else set()

    def prune(self, active_mints: Set[str]) -> None:
        for m in [m for m in self.recent if m not in active_mints]:
            self.recent.pop(m, None)
        for k in [k for k, t in self.pair_tokens.items() if len(t) < 2 and not (t & active_mints)]:
            self.pair_tokens.pop(k, None)
        self._wallet_seen = {x for x in self._wallet_seen if x[1] in active_mints}

    def n_groups(self) -> Tuple[int, int]:
        members = [u for u in self.links if self.is_member(u)]
        seen, groups = set(), 0
        for u in members:
            if u in seen:
                continue
            groups += 1
            stack = [u]
            while stack:
                x = stack.pop()
                if x in seen:
                    continue
                seen.add(x)
                stack.extend(y for y in self.links.get(x, ()) if self.is_member(y) and y not in seen)
        return groups, len(members)


# --------------------------------------------------------------------------- controlador
class PumpPaper:
    def __init__(self, root: Path = PAPER_ROOT, activity=None, rnd: Optional[random.Random] = None):
        self.wallets = WalletBook()
        self.groups = GroupGraph()
        from src.research.niches import NicheHeat
        self.niches = NicheHeat()
        self.niche_done: Set[str] = set()
        self.curves: Dict[str, List[float]] = {}                  # token -> [vsol, vtok, último ts]
        self.meta: Dict[str, Dict[str, Any]] = {}                 # token -> {creator, born, symbol}
        self.accounts = {n: PumpAccount(n, r, root) for n, r in ACCOUNTS.items()}
        self.activity = activity                                  # TokenActivity del recorder (detector viejo)
        self.rnd = rnd or random.Random()
        self.root = Path(root)
        self.group_buys: Dict[str, Dict[str, float]] = {}         # token -> {billetera de grupo: ts de compra}
        self.group_peak: Dict[str, float] = {}                    # token -> máximo de tokens del grupo
        self.signaled: Set[str] = set()
        self.detector_done: Set[str] = set()
        self.x_queue: Deque[str] = deque(maxlen=50)               # para el vigilante de X
        self.signals_log: Deque[Dict[str, Any]] = deque(maxlen=50)
        self.warm = False
        self._last_close = self._last_save = time.time()

    # ---------------------------------------------------------------- precalentamiento con lo grabado
    def warmup(self, base: Path, hours: float = 12.0) -> int:
        """Repite lo grabado (sin operar) para armar grupos y fichas de billeteras."""
        import duckdb
        files = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_trades/**/*.parquet")]
        cfiles = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_creates/**/*.parquet")]
        if not files:
            return 0
        since = int(time.time() - hours * 3600)
        con = duckdb.connect()
        if cfiles:
            for m, cr, u, ts, sy, nm in con.execute(f"""SELECT mint, any_value(creator), any_value("user"),
                    min(ts_chain_s), any_value(symbol), any_value(name) FROM read_parquet({cfiles!r}, union_by_name=true)
                    WHERE ts_chain_s >= {since - 3600} GROUP BY 1""").fetchall():
                self.meta[m] = {"creator": cr or u, "born": float(ts or 0), "symbol": sy or "", "name": nm or ""}
                self.niches.register(m, nm or "", sy or "")
        cur = con.execute(f"""SELECT slot, ts_chain_s, mint, "user", is_buy, sol_amount, token_amount,
            virtual_sol_reserves, virtual_token_reserves FROM (
              SELECT DISTINCT ON (signature, mint, "user", is_buy, sol_amount, token_amount) *
              FROM read_parquet({files!r}, union_by_name=true) WHERE ts_chain_s >= {since}) ORDER BY slot, ts_chain_s""")
        n_rows = 0
        while True:
            chunk = cur.fetchmany(100_000)
            if not chunk:
                break
            for sl, ts, m, u, b, sol, tok, vs, vt in chunk:
                self._ingest({"mint": m, "user": u, "is_buy": b, "sol_amount": sol, "token_amount": tok, "slot": sl,
                              "virtual_sol_reserves": vs, "virtual_token_reserves": vt}, float(ts))
            n_rows += len(chunk)
        self.wallets.close_idle(time.time())
        self.groups.prune(set(self.wallets.mint_last))
        self.group_buys.clear()
        self.group_peak.clear()
        self.warm = True
        g, n = self.groups.n_groups()
        logger.info(f"pump paper precalentado con {n_rows} operaciones: {g} grupos ({n} billeteras)")
        return n_rows

    # ---------------------------------------------------------------- eventos en vivo
    def on_create(self, ev: Dict[str, Any], now: float) -> None:
        self.meta[ev["mint"]] = {"creator": ev.get("creator") or ev.get("user"), "born": now,
                                 "symbol": ev.get("symbol") or "", "name": ev.get("name") or ""}
        self.niches.register(ev["mint"], ev.get("name") or "", ev.get("symbol") or "")

    def on_complete(self, ev: Dict[str, Any], now: float) -> None:
        m = ev["mint"]
        c = self.curves.get(m)
        for a in self.accounts.values():
            if m in a.s["posiciones"]:
                a._fill_sell(m, int(c[0]) if c else 0, int(c[1]) if c else 0, now, "se graduó")
            a.pending_buy.pop(m, None)

    def _group_tokens(self, m: str) -> float:
        return sum(max(self.wallets.pairs.get((u, m), [0, 0, 0])[2], 0.0) for u in self.group_buys.get(m, {}))

    def _ingest(self, ev: Dict[str, Any], now: float) -> Tuple[str, str, bool]:
        m, u, buy = ev["mint"], ev["user"], bool(ev["is_buy"])
        vs, vt = int(ev.get("virtual_sol_reserves") or 0), int(ev.get("virtual_token_reserves") or 0)
        sol, tok = ev["sol_amount"] / LAMPORTS, ev["token_amount"] / TOKEN_UNITS
        self.curves[m] = [vs, vt, now]
        self.wallets.update(u, m, buy, sol, tok, price_sol(vs, vt), now)
        if buy:
            self.groups.on_buy(m, u, int(ev.get("slot") or 0))
        self.niches.add_trade(m, sol, now)
        return m, u, buy

    def on_trade(self, ev: Dict[str, Any], now: float) -> None:
        m, u, buy = self._ingest(ev, now)
        c = self.curves[m]
        for a in self.accounts.values():
            a.on_trade(m, int(c[0]), int(c[1]), now)
        meta = self.meta.get(m) or {}
        if buy and self.groups.is_member(u) and u != meta.get("creator"):
            gb = self.group_buys.setdefault(m, {})
            gb[u] = now
            self._check_signal(m, u, now, meta)
        if buy and m not in self.niche_done and "born" in meta and now - meta["born"] <= SIGNAL["max_age_s"] \
                and u != meta.get("creator") and len(self.wallets.mint_users.get(m, ())) < SIGNAL["max_crowd"]:
            hot = self.niches.hot_keys_of(m, now)
            if hot:
                self.niche_done.add(m)
                self.accounts["nicho"].request_buy(m, now, u, {"symbol": meta.get("symbol", ""), "nichos": hot})
        if m in self.group_buys:                                   # seguimiento de lo que tiene el grupo
            held = self._group_tokens(m)
            self.group_peak[m] = max(self.group_peak.get(m, 0.0), held)
            peak = self.group_peak[m]
            for name in ("grupo", "grupo_nicho"):
                pos = self.accounts[name].s["posiciones"].get(m)
                if pos and peak > 0 and held <= (1 - ACCOUNTS[name]["group_exit"]) * peak:
                    self.accounts[name].mark_sell(m, now, f"el grupo vendió {1 - held / peak:.0%}")

    def _check_signal(self, m: str, u: str, now: float, meta: Dict[str, Any]) -> None:
        if m in self.signaled or "born" not in meta or now - meta["born"] > SIGNAL["max_age_s"]:
            return
        crowd = len(self.wallets.mint_users.get(m, ()))
        if crowd >= SIGNAL["max_crowd"]:
            return
        recent = {w for w, t in self.group_buys[m].items() if now - t <= SIGNAL["within_s"]}
        members = {w for w in recent if w == u or w in self.groups.linked(u)}
        for w in list(members):
            members |= recent & self.groups.linked(w)
        if len(members) < SIGNAL["min_members"]:
            return
        self.signaled.add(m)
        self.group_buys[m] = {w: t for w, t in self.group_buys[m].items() if w in members}
        self.group_peak[m] = self._group_tokens(m)
        hot = self.niches.hot_keys_of(m, now)
        info = {"symbol": meta.get("symbol", ""), "nichos": hot}
        self.accounts["grupo"].request_buy(m, now, u, info)
        if hot:
            self.accounts["grupo_nicho"].request_buy(m, now, u, info)
        self.accounts["grupo_aguantar"].request_buy(m, now, u, info)
        pool = [mm for mm, c in self.curves.items() if mm != m and now - c[2] <= 60
                and now - (self.meta.get(mm) or {}).get("born", -1e18) <= SIGNAL["max_age_s"]
                and len(self.wallets.mint_users.get(mm, ())) < SIGNAL["max_crowd"]
                and not self.accounts["azar"].holds(mm)]
        if pool:
            mm = self.rnd.choice(sorted(pool))
            self.accounts["azar"].request_buy(mm, now, "", {"symbol": (self.meta.get(mm) or {}).get("symbol", "")})
        else:
            self.accounts["azar"].s["senales"] += 1
            self.accounts["azar"].s["saltadas"] += 1
        self.x_queue.append(m)
        self.signals_log.append({"ts": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(), "mint": m,
                                 "simbolo": meta.get("symbol", ""), "billeteras_grupo": len(members),
                                 "gente_en_token": crowd, "edad_min": round((now - meta["born"]) / 60, 1),
                                 "nichos_calientes": hot})
        logger.info(f"Señal GRUPO: {meta.get('symbol', '')} ({m[:6]}…) {len(members)} billeteras de grupo, "
                    f"{crowd} en el token, {round((now - meta['born']) / 60, 1)} min de vida")

    def _detector(self, now: float) -> None:
        if self.activity is None:
            return
        for m in list(self.activity.trades):
            if m in self.detector_done or m not in self.activity.meta:
                continue
            st = self.activity.stats(m, now)
            if st["age_s"] <= 3600 and st["unique_buyers_5m"] >= 50 and st["net_buy_sol_5m"] >= 10:
                self.detector_done.add(m)
                self.accounts["detector_tarde"].request_buy(m, now, "", {"symbol": self.activity.meta[m].get("symbol", "")})

    def tick(self, now: float) -> None:
        self._detector(now)
        for a in self.accounts.values():
            a.tick(now, self.curves)
        if now - self._last_close >= 600:
            self._last_close = now
            self.wallets.close_idle(now)
            held = {m for a in self.accounts.values() for m in list(a.s["posiciones"]) + list(a.pending_buy)}
            for m in [m for m, c in self.curves.items() if now - c[2] > 3 * 3600 and m not in held]:
                for d in (self.curves, self.meta, self.group_buys, self.group_peak):
                    d.pop(m, None)
                self.signaled.discard(m)
                self.niche_done.discard(m)
                self.detector_done.discard(m)
            self.groups.prune(set(self.curves))
            self.niches.prune(now, set(self.curves) | set(self.meta))
            g, n = self.groups.n_groups()
            logger.info(f"pump paper: {g} grupos ({n} billeteras), {len(self.curves)} tokens activos")
        if now - self._last_save >= 30:
            self._last_save = now
            self.save(now)

    def save(self, now: Optional[float] = None) -> None:
        now = now or time.time()
        g, n = self.groups.n_groups()
        top = [{k: (round(v, 2) if isinstance(v, float) and v != float("inf") else (999 if v == float("inf") else v))
                for k, v in r.items()} for r in self.niches.top(now, 12)]
        for a in self.accounts.values():
            a.s["equity"] = a.equity(self.curves)
            a.s["abiertas_valor"] = {m: a.value(m, int(self.curves[m][0]), int(self.curves[m][1]))
                                     for m in a.s["posiciones"] if m in self.curves}
            a.s["actualizado"] = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
            a.s["grupos"], a.s["billeteras_en_grupos"] = g, n
            a.s["ultimas_senales"] = list(self.signals_log)[-15:]
            a.s["nichos_ahora"] = top
            a.save()

    async def run_ticks(self) -> None:
        import asyncio
        while True:
            try:
                await asyncio.sleep(5)
                self.tick(time.time())
            except asyncio.CancelledError:
                self.save()
                break
            except Exception as e:
                logger.warning(f"pump paper: {type(e).__name__}: {str(e)[:150]}")
