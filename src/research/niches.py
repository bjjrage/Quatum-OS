"""Nichos (narrativas): la cripto se mueve fuerte por nichos que rotan en el tiempo, tanto en memes como en Binance.

Memes (pump.fun): cada token se clasifica por nombre/ticker en categorías fijas (IA, gatos, perros, ranas, política,
anime, ...) y además por sus PALABRAS (los memes copian nombres: si "unc" o "troll" aparece en muchos tokens nuevos
con volumen creciente, esa palabra es un nicho). Un nicho está CALIENTE si su volumen de los últimos 30 min es >= 2
veces su promedio por media hora de las últimas 6 h, con >= 5 tokens distintos y >= 20 SOL en esos 30 min.

Binance: mapa fijo de sector para las criptos del laboratorio (IA, memes, L1, L2, DeFi, gaming, infra, RWA, ...).
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple

# --------------------------------------------------------------------------- memes
MEME_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "ia": ("ai", "agent", "gpt", "bot", "neural", "agi", "llm", "grok", "claude", "robot", "cyber"),
    "gatos": ("cat", "kitty", "meow", "neko", "kitten", "popcat", "mew"),
    "perros": ("dog", "doge", "inu", "shib", "pup", "puppy", "wif", "bonk", "doggo", "shiba"),
    "ranas": ("pepe", "frog", "toad", "kek"),
    "politica": ("trump", "maga", "biden", "elon", "musk", "kamala", "melania", "president", "usa", "america", "milei"),
    "anime": ("anime", "waifu", "chan", "kun", "senpai", "manga"),
    "animales": ("monkey", "ape", "chimp", "bear", "bull", "penguin", "hippo", "goat", "fish", "duck", "pig", "rat",
                 "moo", "deng", "seal", "otter", "capy", "capybara", "panda", "hamster"),
    "comida": ("pizza", "burger", "taco", "coffee", "banana", "apple", "cookie", "sushi", "bread", "egg"),
    "religion": ("jesus", "god", "pope", "church", "bible", "angel", "devil", "buddha"),
    "celebridades": ("drake", "kanye", "taylor", "swift", "messi", "ronaldo", "mrbeast", "tate", "diddy"),
}
STOP = {"the", "and", "coin", "token", "sol", "solana", "pump", "fun", "official", "of", "on", "to", "in", "for",
        "inu2", "meme", "memecoin", "new", "first", "real", "baby", "mini", "super", "mega", "king", "lord", "mr"}
_WORD = re.compile(r"[a-z]{3,15}")


def meme_keys(name: str, symbol: str) -> Set[str]:
    """Nichos de un token: categorías fijas ('cat:gatos') + palabras ('w:troll')."""
    text = f"{name or ''} {symbol or ''}".lower()
    words = set(_WORD.findall(text)) - STOP
    keys = {f"w:{w}" for w in words}
    for cat, kws in MEME_CATEGORIES.items():
        if any(k in words or (len(k) >= 4 and k in text) for k in kws):
            keys.add(f"cat:{cat}")
    return keys


class NicheHeat:
    """Volumen por nicho en baldes de 5 minutos (solo pasado)."""

    def __init__(self, bucket_s: int = 300, hot_window_s: int = 1800, base_window_s: int = 6 * 3600,
                 min_ratio: float = 2.0, min_tokens: int = 5, min_sol: float = 20.0):
        self.bucket_s, self.hot_s, self.base_s = bucket_s, hot_window_s, base_window_s
        self.min_ratio, self.min_tokens, self.min_sol = min_ratio, min_tokens, min_sol
        self.b: Dict[str, Deque[List]] = defaultdict(deque)       # nicho -> [[balde, sol, set(tokens)], ...]
        self.mint_keys: Dict[str, Set[str]] = {}

    def register(self, mint: str, name: str, symbol: str) -> Set[str]:
        k = meme_keys(name, symbol)
        self.mint_keys[mint] = k
        return k

    def add_trade(self, mint: str, sol: float, ts: float) -> None:
        bk = int(ts // self.bucket_s)
        for key in self.mint_keys.get(mint, ()):
            dq = self.b[key]
            if dq and dq[-1][0] == bk:
                dq[-1][1] += sol
                dq[-1][2].add(mint)
            else:
                dq.append([bk, sol, {mint}])
            while dq and (bk - dq[0][0]) * self.bucket_s > self.base_s:
                dq.popleft()

    def stats(self, key: str, now: float) -> Dict[str, float]:
        bk = int(now // self.bucket_s)
        hot_b, base_b = self.hot_s // self.bucket_s, self.base_s // self.bucket_s
        recent = [x for x in self.b.get(key, ()) if bk - x[0] < hot_b]
        older = [x for x in self.b.get(key, ()) if hot_b <= bk - x[0] < base_b]
        vol = sum(x[1] for x in recent)
        toks = len(set().union(*[x[2] for x in recent])) if recent else 0
        base = sum(x[1] for x in older) / max((base_b - hot_b) / hot_b, 1.0)
        return {"sol_30m": vol, "tokens_30m": toks, "base_sol_30m": base,
                "ratio": vol / base if base > 0 else (float("inf") if vol > 0 else 0.0)}

    def is_hot(self, key: str, now: float) -> bool:
        s = self.stats(key, now)
        return s["sol_30m"] >= self.min_sol and s["tokens_30m"] >= self.min_tokens and s["ratio"] >= self.min_ratio

    def hot_keys_of(self, mint: str, now: float) -> List[str]:
        return [k for k in self.mint_keys.get(mint, ()) if self.is_hot(k, now)]

    def top(self, now: float, n: int = 10) -> List[Dict[str, float]]:
        out = []
        for key in list(self.b):
            s = self.stats(key, now)
            if s["sol_30m"] > 0:
                out.append({"nicho": key, **s, "caliente": self.is_hot(key, now)})
        out.sort(key=lambda r: (-int(r["caliente"]), -r["sol_30m"]))
        return out[:n]

    def prune(self, now: float, active_mints: Iterable[str]) -> None:
        bk = int(now // self.bucket_s)
        for key in [k for k, dq in self.b.items() if not dq or (bk - dq[-1][0]) * self.bucket_s > self.base_s]:
            self.b.pop(key, None)
        act = set(active_mints)
        for m in [m for m in self.mint_keys if m not in act]:
            self.mint_keys.pop(m, None)


# --------------------------------------------------------------------------- Binance (sectores)
SECTORS: Dict[str, Tuple[str, ...]] = {
    "ia": ("FET", "RENDER", "RNDR", "TAO", "WLD", "AGIX", "OCEAN", "ARKM", "AI", "NFP", "VIRTUAL", "AIXBT", "GRASS",
           "IO", "PHB", "AI16Z", "GRT"),
    "memes": ("DOGE", "1000SHIB", "SHIB", "1000PEPE", "PEPE", "WIF", "1000BONK", "BONK", "1000FLOKI", "FLOKI", "MEME",
              "BOME", "POPCAT", "NEIRO", "PNUT", "TRUMP", "PEOPLE", "TURBO", "MEW", "1000SATS", "ORDI", "NOT", "DOGS",
              "BRETT", "GOAT", "MOODENG", "FARTCOIN", "PENGU"),
    "l1": ("BTC", "ETH", "SOL", "BNB", "ADA", "AVAX", "DOT", "ATOM", "NEAR", "APT", "SUI", "SEI", "TIA", "INJ", "TON",
           "TRX", "XRP", "LTC", "BCH", "ETC", "ALGO", "HBAR", "ICP", "FTM", "S", "KAS", "EGLD", "XLM", "HYPE", "BERA",
           "KAIA", "XTZ", "EOS", "NEO", "VET", "FIL", "XMR", "ZEC", "DASH", "CFX", "ROSE", "MINA", "ONE", "KAVA"),
    "l2": ("ARB", "OP", "MATIC", "POL", "STRK", "ZK", "MANTA", "METIS", "IMX", "BLAST", "SCR", "TAIKO", "MNT", "STX",
           "LRC", "SKL", "CELO", "ZRO", "DYM", "ALT", "SAGA", "W", "OMNI"),
    "defi": ("UNI", "AAVE", "MKR", "LDO", "CRV", "COMP", "SNX", "DYDX", "GMX", "PENDLE", "JUP", "RAY", "SUSHI", "1INCH",
             "CAKE", "ENA", "ETHFI", "EIGEN", "JTO", "RUNE", "LQTY", "BAL", "YFI", "ZRX", "ENS", "SSV", "RPL", "FXS",
             "AEVO", "PERP", "UMA", "BAND", "API3", "AERO", "MORPHO", "CVX", "COW", "BANANA"),
    "gaming": ("AXS", "SAND", "MANA", "GALA", "ILV", "YGG", "PIXEL", "BEAM", "MAGIC", "APE", "ENJ", "SUPER", "PORTAL",
               "XAI", "PYR", "BEAMX", "RONIN", "VANRY", "ALICE", "GMT", "VOXEL", "BIGTIME", "NFT", "BLUR", "MAVIA", "ACE", "PRIME"),
    "infra": ("LINK", "PYTH", "AR", "STORJ", "THETA", "HNT", "IOTX", "ANKR", "QNT", "AXL", "TRB", "AKT", "ZETA",
              "CKB", "JASMY", "ONT", "IOST", "ICX", "CHZ", "RSR", "MASK", "TNSR", "ID", "CYBER", "LPT"),
    "rwa": ("ONDO", "OM", "POLYX", "CFG", "TRU", "PLUME"),
}


def sector_of(symbol: str) -> Optional[str]:
    base = symbol.upper().replace("USDT", "")
    for sec, names in SECTORS.items():
        if base in names:
            return sec
    return None


def sector_map(symbols: Iterable[str]) -> Dict[str, str]:
    """símbolo -> sector (los que no tienen sector quedan afuera)."""
    out = {}
    for s in symbols:
        sec = sector_of(s)
        if sec:
            out[s] = sec
    return out
