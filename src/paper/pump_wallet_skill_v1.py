"""Canonical pump.fun forward paper for WALLET_SKILL_V1.

Frozen research hypothesis:
- A wallet is GOOD only from matured prior observations: >=5 tokens, >=35% hit 2x.
- Every wallet-token observation matures exactly 2h after the wallet's first buy.
  Winners and failures are credited at the same maturity time (deferred credit).
- Signal fires exactly when the 10th unique buyer appears and >=2 of the first 10
  are GOOD using only information available at that decision time.
- Entry is the next trade after the decision.
- Paper sizing is fixed 0.5 SOL, 20 SOL initial capital, max 30 open positions.
- Exit: take 50% at 2x, trail remainder 35%, -50% stop before 2x, 2h timeout,
  6h safety max hold.

This module intentionally does NOT run the older group/niche experiments. Those
remain on disk/read-only as archived evidence.
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
from src.paper.pump_paper import FEE, TX_SOL, PUMP_FEE_MODEL, buy_tokens, sell_sol, price_sol

logger = setup_logger("pump_wallet_skill_v1")

ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = ROOT / "data" / "paper"

RULES_VERSION = "WALLET_SKILL_V1"
GOOD_MIN_MATURED = 5
GOOD_MIN_HIT_RATE = 0.35
EVAL_HORIZON_S = 2 * 3600
FIRST_BUYERS = 10
MIN_GOOD_IN_FIRST = 2
INITIAL_CAPITAL_SOL = 20.0
ENTRY_SOL = 0.5
MAX_OPEN = 30
FILL_TIMEOUT_S = 15
STOP_LOSS = -0.50
TAKE_AT = 1.0
TAKE_FRAC = 0.50
TRAIL = 0.35
MAX_WAIT_S = 2 * 3600
MAX_HOLD_S = 6 * 3600
SNAPSHOT_FORMAT = 1
SNAPSHOT_EVERY_S = 600            # the full wallet state is large: persist it every 10 min and on shutdown
CATCHUP_OVERLAP_S = 300           # replay a little before the snapshot cutoff; replays are idempotent
MATURED_MEMORY_S = 24 * 3600      # how long a matured (wallet, token) key is remembered to reject replays

ACTIVE_ACCOUNTS = {
    "wallet_ladder_v1": "WALLET_SKILL_V1 — 2 good wallets in first 10; ladder exit",
    "wallet_random_v1": "CONTROL — matched live token at the same wallet-skill signal time",
}

ARCHIVED_ACCOUNTS = {
    "grupo": "ARCHIVED_REJECTED",
    "grupo_nicho": "ARCHIVED_REJECTED",
    "nicho": "ARCHIVED_REJECTED",
    "grupo_aguantar": "ARCHIVED_REJECTED",
    "detector_tarde": "ARCHIVED_REJECTED",
    "azar": "CONTROL_ARCHIVED",
}


class WalletSkillBook:
    """Point-in-time wallet skill with symmetric 2h deferred credit."""

    def __init__(self):
        self.stats: Dict[str, Dict[str, int]] = {}
        self.pending: Dict[Tuple[str, str], Dict[str, float]] = {}
        self.pending_by_mint: Dict[str, Set[Tuple[str, str]]] = {}
        self.matured_keys: Dict[Tuple[str, str], float] = {}   # key -> matured at; rejects replayed observations

    def to_dict(self) -> Dict[str, Any]:
        return {"stats": {w: [s.get("matured", 0), s.get("wins", 0)] for w, s in self.stats.items()},
                "pending": [[w, m, o["entry_ts"], o["entry_price"], o["matures_at"], o["peak_multiple"]]
                            for (w, m), o in self.pending.items()],
                "matured_keys": [[w, m, t] for (w, m), t in self.matured_keys.items()]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WalletSkillBook":
        b = cls()
        b.stats = {w: {"matured": int(v[0]), "wins": int(v[1])} for w, v in (d.get("stats") or {}).items()}
        for w, m, entry_ts, entry_price, matures_at, peak in d.get("pending") or []:
            b.pending[(w, m)] = {"entry_ts": float(entry_ts), "entry_price": float(entry_price),
                                 "matures_at": float(matures_at), "peak_multiple": float(peak)}
            b.pending_by_mint.setdefault(m, set()).add((w, m))
        b.matured_keys = {(w, m): float(t) for w, m, t in d.get("matured_keys") or []}
        return b

    def is_good(self, wallet: str) -> bool:
        s = self.stats.get(wallet) or {}
        n, wins = int(s.get("matured", 0)), int(s.get("wins", 0))
        return n >= GOOD_MIN_MATURED and wins / n >= GOOD_MIN_HIT_RATE

    def snapshot(self, wallet: str) -> Dict[str, Any]:
        s = self.stats.get(wallet) or {}
        n, wins = int(s.get("matured", 0)), int(s.get("wins", 0))
        return {
            "wallet": wallet,
            "matured": n,
            "wins_2x": wins,
            "hit_rate_2x": (wins / n) if n else None,
            "good": self.is_good(wallet),
        }

    def good_count(self) -> int:
        return sum(1 for w in self.stats if self.is_good(w))

    def mature(self, now: float) -> int:
        keys = [k for k, o in self.pending.items() if o["matures_at"] <= now]
        for key in keys:
            o = self.pending.pop(key)
            wallet, mint = key
            self.matured_keys[key] = now
            s = self.stats.setdefault(wallet, {"matured": 0, "wins": 0})
            s["matured"] += 1
            if o["peak_multiple"] >= 2.0:
                s["wins"] += 1
            bucket = self.pending_by_mint.get(mint)
            if bucket:
                bucket.discard(key)
                if not bucket:
                    self.pending_by_mint.pop(mint, None)
        if len(self.matured_keys) > 50_000 and keys:
            cut = now - MATURED_MEMORY_S
            self.matured_keys = {k: t for k, t in self.matured_keys.items() if t >= cut}
        return len(keys)

    def on_trade(self, wallet: str, mint: str, is_buy: bool, px: float, now: float) -> None:
        self.mature(now)
        if px > 0:
            for key in list(self.pending_by_mint.get(mint, ())):
                o = self.pending.get(key)
                if o and o["entry_price"] > 0:
                    o["peak_multiple"] = max(o["peak_multiple"], px / o["entry_price"])
        if is_buy and px > 0:
            key = (wallet, mint)
            if key not in self.pending and key not in self.matured_keys:
                self.pending[key] = {
                    "entry_ts": now,
                    "entry_price": px,
                    "matures_at": now + EVAL_HORIZON_S,
                    "peak_multiple": 1.0,
                }
                self.pending_by_mint.setdefault(mint, set()).add(key)


class FixedPumpAccount:
    def __init__(self, name: str, root: Path = PAPER_ROOT):
        self.name = name
        self.path = Path(root) / f"pump_{name}" / "state.json"
        self.s: Dict[str, Any] = {
            "strategy": RULES_VERSION,
            "capital_inicial": INITIAL_CAPITAL_SOL,
            "cash": INITIAL_CAPITAL_SOL,
            "entry_sol": ENTRY_SOL,
            "max_abiertas": MAX_OPEN,
            "posiciones": {},
            "cerradas": [],
            "n_cerradas": 0,
            "ganadas": 0,
            "resultado_sol": 0.0,
            "comisiones_sol": 0.0,
            "senales": 0,
            "saltadas": 0,
            "tomas_2x": 0,
            "creado": datetime.now(timezone.utc).isoformat(),
            "descripcion": ACTIVE_ACCOUNTS[name],
        }
        if self.path.exists():
            try:
                prior = json.loads(self.path.read_text(encoding="utf-8"))
                if prior.get("strategy") == RULES_VERSION:
                    self.s.update(prior)
            except Exception:
                logger.warning("%s state unreadable; starting a fresh paper state", name)
        self.pending_buy: Dict[str, Dict[str, Any]] = {}
        self.pending_sell: Dict[str, Tuple[float, str, float]] = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def holds(self, mint: str) -> bool:
        return mint in self.s["posiciones"] or mint in self.pending_buy

    def request_buy(self, mint: str, now: float, info: Optional[Dict[str, Any]] = None) -> bool:
        self.s["senales"] += 1
        if self.holds(mint) or len(self.s["posiciones"]) + len(self.pending_buy) >= MAX_OPEN \
                or self.s["cash"] < ENTRY_SOL + TX_SOL:
            self.s["saltadas"] += 1
            return False
        self.pending_buy[mint] = {"ts": now, **(info or {})}
        return True

    def note_unmatched_control(self) -> None:
        self.s["senales"] += 1
        self.s["saltadas"] += 1

    def _fill_buy(self, mint: str, vsol: int, vtok: int, now: float) -> None:
        req = self.pending_buy.pop(mint)
        size = ENTRY_SOL
        if self.s["cash"] < size + TX_SOL:
            self.s["saltadas"] += 1
            return
        tok = buy_tokens(size, vsol, vtok)
        if tok <= 0:
            return
        self.s["cash"] -= size + TX_SOL
        self.s["comisiones_sol"] += size * FEE + TX_SOL
        cost = size + TX_SOL
        self.s["posiciones"][mint] = {
            "tok": tok,
            "costo": cost,
            "costo_restante": cost,
            "cobrado": 0.0,
            "max_valor": cost,
            "tomado": False,
            "entrada_ts": now,
            "precio_entrada": price_sol(vsol, vtok),
            "simbolo": req.get("symbol", ""),
            "decision_ts": req.get("decision_ts"),
            "decision_slot": req.get("decision_slot"),
            "good_wallets": req.get("good_wallets", []),
            "first_10_wallets": req.get("first_10_wallets", []),
            "demora_s": round(now - req["ts"], 3),
        }

    def _fill_sell(self, mint: str, vsol: int, vtok: int, now: float, reason: str, frac: float = 1.0) -> None:
        pos = self.s["posiciones"].get(mint)
        self.pending_sell.pop(mint, None)
        if not pos:
            return
        q = pos["tok"] * min(max(frac, 0.0), 1.0)
        got = max(sell_sol(q, vsol, vtok) - TX_SOL, 0.0)
        self.s["cash"] += got
        self.s["comisiones_sol"] += (got * FEE / (1 - FEE) if got else 0.0) + TX_SOL
        pos["cobrado"] += got
        if frac < 0.999 and q < pos["tok"]:
            pos["costo_restante"] *= (pos["tok"] - q) / pos["tok"]
            pos["tok"] -= q
            pos["tomado"] = True
            pos["max_valor"] = 0.0
            self.s["tomas_2x"] += 1
            return
        del self.s["posiciones"][mint]
        pnl = pos["cobrado"] - pos["costo"]
        self.s["n_cerradas"] += 1
        self.s["ganadas"] += 1 if pnl > 0 else 0
        self.s["resultado_sol"] += pnl
        self.s["cerradas"] = (self.s["cerradas"] + [{
            "mint": mint,
            "simbolo": pos.get("simbolo", ""),
            "pnl_sol": pnl,
            "multiplo": pos["cobrado"] / pos["costo"] if pos["costo"] else None,
            "motivo": reason,
            "tomo_2x": pos["tomado"],
            "minutos": round((now - pos["entrada_ts"]) / 60, 1),
            "cerrada": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        }])[-300:]

    def value(self, mint: str, vsol: int, vtok: int) -> float:
        pos = self.s["posiciones"].get(mint)
        return max(sell_sol(pos["tok"], vsol, vtok) - TX_SOL, 0.0) if pos else 0.0

    def mark_sell(self, mint: str, now: float, reason: str, frac: float = 1.0) -> None:
        cur = self.pending_sell.get(mint)
        if mint in self.s["posiciones"] and (cur is None or frac > cur[2]):
            self.pending_sell[mint] = (now, reason, frac)

    def on_trade(self, mint: str, vsol: int, vtok: int, now: float) -> None:
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
        val = self.value(mint, vsol, vtok)
        pos["max_valor"] = max(pos["max_valor"], val)
        if not pos["tomado"]:
            ret = val / pos["costo"] - 1
            if ret >= TAKE_AT:
                self.mark_sell(mint, now, "2x", TAKE_FRAC)
            elif ret <= STOP_LOSS:
                self.mark_sell(mint, now, "stop -50%")
        elif val <= (1 - TRAIL) * pos["max_valor"]:
            self.mark_sell(mint, now, "trailing -35%")

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
            if not pos["tomado"] and age >= MAX_WAIT_S:
                self.mark_sell(mint, now, "no llego a 2x en 2h")
            elif age >= MAX_HOLD_S:
                self.mark_sell(mint, now, "tope 6h")
        for mint, (ts, reason, frac) in list(self.pending_sell.items()):
            if now - ts >= FILL_TIMEOUT_S:
                c = curves.get(mint)
                self._fill_sell(mint, int(c[0]) if c else 0, int(c[1]) if c else 0, now, reason, frac)

    def force_close(self, mint: str, curve: Optional[List[float]], now: float, reason: str) -> None:
        if mint in self.pending_buy:
            self.pending_buy.pop(mint, None)
        if mint in self.s["posiciones"]:
            self._fill_sell(mint, int(curve[0]) if curve else 0, int(curve[1]) if curve else 0, now, reason)

    def equity(self, curves: Dict[str, List[float]]) -> float:
        return self.s["cash"] + sum(
            self.value(m, int(curves[m][0]), int(curves[m][1]))
            for m in self.s["posiciones"] if m in curves
        )


class WalletSkillPaper:
    def __init__(self, root: Path = PAPER_ROOT, rnd: Optional[random.Random] = None, restore: bool = True):
        self.root = Path(root)
        self.skill = WalletSkillBook()
        self.accounts = {n: FixedPumpAccount(n, self.root) for n in ACTIVE_ACCOUNTS}
        self.curves: Dict[str, List[float]] = {}
        self.meta: Dict[str, Dict[str, Any]] = {}
        self.buyers: Dict[str, List[str]] = {}
        self.buyer_sets: Dict[str, Set[str]] = {}
        self.last_trade: Dict[str, float] = {}
        self.signaled: Set[str] = set()
        self.signals_log: Deque[Dict[str, Any]] = deque(maxlen=100)
        self.x_queue: Deque[str] = deque(maxlen=50)
        self.rnd = rnd or random.Random(7)
        self._last_save = time.time()
        self._last_snapshot = float("-inf")
        self.last_event_ts = 0.0                 # newest event ingested (snapshot cutoff)
        self.snapshot_cutoff: Optional[float] = None
        self.snapshot_path = self.root / "pump_wallet_skill_v1" / "bootstrap_snapshot.json"
        if restore and self.snapshot_path.exists():
            try:
                self.load_bootstrap_snapshot(self.snapshot_path)
            except ValueError as exc:
                logger.warning("%s; the next bootstrap rebuilds from history", exc)

    def load_bootstrap_snapshot(self, path: Path) -> float:
        """Restore the canonical wallet state. Raises ValueError('SNAPSHOT_INVALID: ...') on a corrupt or
        incompatible file instead of silently starting from a partial state. Returns the snapshot cutoff."""
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"SNAPSHOT_INVALID: unreadable ({type(exc).__name__})") from exc
        if not isinstance(d, dict) or d.get("format") != SNAPSHOT_FORMAT or d.get("rules") != RULES_VERSION:
            raise ValueError("SNAPSHOT_INVALID: incompatible format or rules version")
        try:
            skill = WalletSkillBook.from_dict(d["skill"])
            buyers = {m: list(ws) for m, ws in (d.get("buyers") or {}).items()}
            cutoff = float(d["cutoff_ts"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"SNAPSHOT_INVALID: malformed ({type(exc).__name__})") from exc
        self.skill = skill
        self.buyers = buyers
        self.buyer_sets = {m: set(ws) for m, ws in buyers.items()}
        self.signaled = set(d.get("signaled") or [])
        self.meta = dict(d.get("meta") or {})
        self.curves = {m: list(c) for m, c in (d.get("curves") or {}).items()}
        self.last_trade = {m: float(t) for m, t in (d.get("last_trade") or {}).items()}
        self.last_event_ts = self.snapshot_cutoff = cutoff
        return cutoff

    def save_bootstrap_snapshot(self, now: float) -> None:
        active = set(self.buyers) | set(self.curves)
        payload = {"format": SNAPSHOT_FORMAT, "rules": RULES_VERSION, "saved_at": now,
                   "cutoff_ts": self.last_event_ts, "skill": self.skill.to_dict(), "buyers": self.buyers,
                   "signaled": sorted(self.signaled & active), "meta": self.meta, "curves": self.curves,
                   "last_trade": self.last_trade}
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.snapshot_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self.snapshot_path)
        self._last_snapshot = now

    def bootstrap(self, base: Path) -> int:
        """Bring the state up to date: replay only what came after the snapshot, or the full history if there is
        no valid snapshot. Runs before live events are delivered (the recorder buffers them meanwhile)."""
        if self.snapshot_cutoff is not None:
            return self.warmup(base, since_ts=self.snapshot_cutoff - CATCHUP_OVERLAP_S)
        return self.warmup(base)

    def on_create(self, ev: Dict[str, Any], now: float) -> None:
        self.meta[ev["mint"]] = {
            "creator": ev.get("creator") or ev.get("user"),
            "born": float(ev.get("ts_chain_s") or now),
            "symbol": ev.get("symbol") or "",
            "name": ev.get("name") or "",
        }

    def _remember_buyer(self, mint: str, wallet: str) -> bool:
        seen = self.buyer_sets.setdefault(mint, set())
        if wallet in seen:
            return False
        seen.add(wallet)
        self.buyers.setdefault(mint, []).append(wallet)
        return True

    def _control_candidate(self, signal_mint: str, now: float) -> Optional[str]:
        pool = []
        for mint, buyers in self.buyers.items():
            if mint == signal_mint or self.accounts["wallet_random_v1"].holds(mint):
                continue
            n = len(buyers)
            if 8 <= n <= 12 and now - self.last_trade.get(mint, 0) <= 60:
                pool.append(mint)
        return self.rnd.choice(sorted(pool)) if pool else None

    def _maybe_signal(self, mint: str, now: float, slot: int) -> None:
        buyers = self.buyers.get(mint, [])
        if mint in self.signaled or len(buyers) != FIRST_BUYERS:
            return
        first10 = buyers[:FIRST_BUYERS]
        snapshots = [self.skill.snapshot(w) for w in first10]
        good = [s["wallet"] for s in snapshots if s["good"]]
        if len(good) < MIN_GOOD_IN_FIRST:
            return
        self.signaled.add(mint)
        meta = self.meta.get(mint) or {}
        info = {
            "symbol": meta.get("symbol", ""),
            "decision_ts": now,
            "decision_slot": slot,
            "first_10_wallets": first10,
            "good_wallets": good,
        }
        self.accounts["wallet_ladder_v1"].request_buy(mint, now, info)
        control = self._control_candidate(mint, now)
        if control:
            cm = self.meta.get(control) or {}
            self.accounts["wallet_random_v1"].request_buy(control, now, {
                "symbol": cm.get("symbol", ""),
                "decision_ts": now,
                "decision_slot": slot,
                "matched_to": mint,
            })
        else:
            self.accounts["wallet_random_v1"].note_unmatched_control()
        self.x_queue.append(mint)
        self.signals_log.append({
            "ts": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "mint": mint,
            "simbolo": meta.get("symbol", ""),
            "buyer_count": FIRST_BUYERS,
            "good_wallets": good,
            "good_wallet_count": len(good),
            "control_mint": control,
        })
        logger.info("WALLET_SKILL_V1 signal %s %s good wallets among first 10", mint[:8], len(good))

    def _ingest(self, ev: Dict[str, Any], now: float, allow_signal: bool = True, remember_buyer: bool = True) -> None:
        mint, wallet, is_buy = ev["mint"], ev["user"], bool(ev["is_buy"])
        vsol, vtok = int(ev.get("virtual_sol_reserves") or 0), int(ev.get("virtual_token_reserves") or 0)
        px = price_sol(vsol, vtok)
        self.last_event_ts = max(self.last_event_ts, now)
        self.curves[mint] = [vsol, vtok, now]
        self.last_trade[mint] = now
        self.skill.on_trade(wallet, mint, is_buy, px, now)
        if is_buy and remember_buyer:
            added = self._remember_buyer(mint, wallet)
            if added and allow_signal:
                self._maybe_signal(mint, now, int(ev.get("slot") or 0))

    def on_trade(self, ev: Dict[str, Any], now: float) -> None:
        mint = ev["mint"]
        # Existing pending entries/exits see this trade first. Therefore a signal
        # created by this same trade cannot fill until the following trade.
        c0 = self.curves.get(mint)
        if c0 is not None:
            for a in self.accounts.values():
                a.on_trade(mint, int(ev.get("virtual_sol_reserves") or 0),
                           int(ev.get("virtual_token_reserves") or 0), now)
        self._ingest(ev, now, allow_signal=True, remember_buyer=True)

    def on_complete(self, ev: Dict[str, Any], now: float) -> None:
        mint = ev["mint"]
        curve = self.curves.get(mint)
        for a in self.accounts.values():
            a.force_close(mint, curve, now, "se graduo")

    def warmup(self, base: Path, since_ts: Optional[float] = None) -> int:
        """Rebuild point-in-time wallet skill from raw history without paper trading (only after `since_ts` if
        given: incremental catch-up from a snapshot)."""
        import duckdb

        files = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_trades/**/*.parquet")]
        creates = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_creates/**/*.parquet")]
        if not files:
            return 0
        now = time.time()
        recent_cut = now - 3 * 3600
        lo = int(since_ts) if since_ts is not None else 1577836800
        con = duckdb.connect()
        if creates:
            q = f"""SELECT mint, any_value(creator), any_value("user"), min(ts_chain_s),
                    any_value(symbol), any_value(name)
                    FROM read_parquet({creates!r}, union_by_name=true)
                    WHERE ts_chain_s BETWEEN 1577836800 AND {int(now + 300)}
                    GROUP BY 1"""
            for mint, creator, user, born, symbol, name in con.execute(q).fetchall():
                if float(born or 0) >= recent_cut - 3600:
                    self.meta[mint] = {
                        "creator": creator or user,
                        "born": float(born or 0),
                        "symbol": symbol or "",
                        "name": name or "",
                    }
        q = f"""SELECT slot, ts_chain_s, mint, "user", is_buy, virtual_sol_reserves, virtual_token_reserves
                FROM (
                  SELECT DISTINCT ON (signature, mint, "user", is_buy, sol_amount, token_amount) *
                  FROM read_parquet({files!r}, union_by_name=true)
                  WHERE ts_chain_s BETWEEN {lo} AND {int(now + 300)}
                )
                ORDER BY ts_chain_s, slot"""
        cur = con.execute(q)
        n = 0
        while True:
            rows = cur.fetchmany(100_000)
            if not rows:
                break
            for slot, ts, mint, user, is_buy, vsol, vtok in rows:
                event = {
                    "slot": slot,
                    "mint": mint,
                    "user": user,
                    "is_buy": is_buy,
                    "virtual_sol_reserves": vsol,
                    "virtual_token_reserves": vtok,
                }
                self._ingest(event, float(ts), allow_signal=False, remember_buyer=float(ts) >= recent_cut)
            n += len(rows)
        self.skill.mature(now)
        logger.info("wallet skill warmup: %s trades, %s good wallets", n, self.skill.good_count())
        return n

    def tick(self, now: float) -> None:
        self.skill.mature(now)
        for a in self.accounts.values():
            a.tick(now, self.curves)
        # Keep only active-token buyer memory; wallet skill stats remain cumulative.
        stale = [m for m, ts in self.last_trade.items() if now - ts > 3 * 3600]
        held = {m for a in self.accounts.values() for m in list(a.s["posiciones"]) + list(a.pending_buy)}
        for mint in stale:
            if mint in held:
                continue
            self.buyers.pop(mint, None)
            self.buyer_sets.pop(mint, None)
            self.curves.pop(mint, None)
            self.last_trade.pop(mint, None)
            self.meta.pop(mint, None)
        if now - self._last_save >= 30:
            self._last_save = now
            self.save(now)

    def save(self, now: Optional[float] = None, snapshot: Optional[bool] = None) -> None:
        now = now or time.time()
        if snapshot or (snapshot is None and now - self._last_snapshot >= SNAPSHOT_EVERY_S):
            self.save_bootstrap_snapshot(now)
        for a in self.accounts.values():
            a.s["equity"] = a.equity(self.curves)
            a.s["actualizado"] = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
            a.s["good_wallets_current"] = self.skill.good_count()
            a.s["rules_version"] = RULES_VERSION
            a.save()
        path = self.root / "pump_wallet_skill_v1" / "status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "strategy": RULES_VERSION,
            "research_status": "PAPER_FORWARD_UNVALIDATED",
            "economics_status": PUMP_FEE_MODEL["status"],
            "good_wallets_current": self.skill.good_count(),
            "signals": len(self.signals_log),
            "recent_signals": list(self.signals_log)[-20:],
            "updated": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "rules": {
                "min_matured_tokens": GOOD_MIN_MATURED,
                "min_hit_rate_2x": GOOD_MIN_HIT_RATE,
                "deferred_credit_seconds": EVAL_HORIZON_S,
                "first_unique_buyers": FIRST_BUYERS,
                "min_good_wallets": MIN_GOOD_IN_FIRST,
                "entry_sol": ENTRY_SOL,
                "initial_capital_sol": INITIAL_CAPITAL_SOL,
                "max_open": MAX_OPEN,
            },
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        tmp.replace(path)

    async def run_ticks(self) -> None:
        import asyncio
        from src.common.runtime_health import RuntimeHealth
        health = RuntimeHealth("pumpfun_paper", ROOT)
        while True:
            try:
                await asyncio.sleep(5)
                self.tick(time.time())
                health.update("RUNNING", success=True, strategy=RULES_VERSION)
            except asyncio.CancelledError:
                self.save()
                health.update("STOPPED")
                break
            except Exception as exc:
                health.update("DEGRADED", error=exc)
                logger.warning("wallet skill paper: %s: %s", type(exc).__name__, str(exc)[:160])
