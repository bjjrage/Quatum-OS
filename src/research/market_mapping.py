"""Polymarket crypto-threshold market -> pricing specification.

STR-001 compares a Polymarket YES price with the Deribit risk-neutral probability that
``S(T) > K`` (a *digital*). That comparison is only valid for markets that really are digitals
at a known time against a known underlying. Everything else is REJECTED with an explicit
reason (UNKNOWN != SAFE):

* "hit / reach / touch / dip to X" are barrier (touch) products: worth up to ~2x a digital.
* Markets without an explicit strike, underlying or resolution time.
* Question date and market end date that disagree by more than 36 hours.

Resolution time: Polymarket's daily/weekly crypto markets resolve on the Binance 1-minute candle
close at 12:00 ET (America/New_York) of the stated date; Deribit options expire 08:00 UTC. The two
clocks differ, so the surface module interpolates total variance in time instead of snapping.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

_UNDERLYING_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("BTC", re.compile(r"\b(bitcoin|btc)\b", re.IGNORECASE)),
    ("ETH", re.compile(r"\b(ethereum|ether|eth)\b", re.IGNORECASE)),
    ("SOL", re.compile(r"\b(solana|sol)\b", re.IGNORECASE)),
]
_TOUCH_RE = re.compile(
    r"\b(hit|hits|reach|reaches|touch|touches|dip|dips|fall to|falls to|drop to|drops to|"
    r"crosses?|exceeds? at any|at any point|any time|ever)\b", re.IGNORECASE)
_ABOVE_RE = re.compile(r"\b(above|over|greater than|higher than|more than|at least|exceed)\b|>", re.IGNORECASE)
_BELOW_RE = re.compile(r"\b(below|under|less than|lower than|at most)\b|<", re.IGNORECASE)
_BETWEEN_RE = re.compile(r"\bbetween\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*([kKmM]?)\b")
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], start=1)}
_MONTH_ABBR = {k[:3]: v for k, v in _MONTHS.items()}
_DATE_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+([0-9]{1,2})(?:st|nd|rd|th)?"
    r"(?:,?\s*(20[0-9]{2}))?\b", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedQuestion:
    underlying: str            # BTC | ETH | SOL
    kind: str                  # ABOVE | BELOW | RANGE
    strike_lo: float           # ABOVE/BELOW: the strike; RANGE: lower bound
    strike_hi: Optional[float]  # RANGE only
    resolve_utc: datetime      # tz-aware UTC resolution instant
    note: str = ""


@dataclass(frozen=True)
class MappedMarket:
    market_id: str
    question: str
    yes_token_id: str
    no_token_id: Optional[str]
    parsed: ParsedQuestion
    description: str = ""


@dataclass(frozen=True)
class RejectedMarket:
    market_id: str
    question: str
    reason: str


def _to_number(txt: str, suffix: str) -> float:
    v = float(txt.replace(",", ""))
    s = suffix.lower()
    return v * (1_000.0 if s == "k" else 1_000_000.0 if s == "m" else 1.0)


def _detect_underlying(q: str) -> Optional[str]:
    hits = [u for u, rx in _UNDERLYING_PATTERNS if rx.search(q)]
    return hits[0] if len(hits) == 1 else None  # ambiguous (two assets) -> reject


def _strikes(q: str) -> List[float]:
    """Extract dollar-like numbers; ignores bare small integers that are dates/years."""
    # remove date expressions first so "October 31" / "2026" never become strikes
    cleaned = _DATE_RE.sub(" ", q)
    cleaned = re.sub(r"\b20[0-9]{2}\b", " ", cleaned)
    cleaned = re.sub(r"\b[0-9]{1,2}\s*(?:am|pm)\b", " ", cleaned, flags=re.IGNORECASE)
    out = []
    for m in _NUM_RE.finditer(cleaned):
        out.append(_to_number(m.group(1), m.group(2)))
    return [v for v in out if v > 0.0]


def _question_date(q: str, ref: datetime) -> Optional[date]:
    m = _DATE_RE.search(q)
    if not m:
        return None
    mon_txt = m.group(1).lower().rstrip(".")
    month = _MONTHS.get(mon_txt) or _MONTH_ABBR.get(mon_txt[:3])
    if not month:
        return None
    day = int(m.group(2))
    year = int(m.group(3)) if m.group(3) else None
    try:
        if year is not None:
            return date(year, month, day)
        best: Optional[date] = None
        for y in (ref.year - 1, ref.year, ref.year + 1):  # pick the year closest to the market end date
            cand = date(y, month, day)
            if best is None or abs((cand - ref.date()).days) < abs((best - ref.date()).days):
                best = cand
        return best
    except ValueError:
        return None


def _parse_end(end_iso: str) -> Optional[datetime]:
    if not end_iso:
        return None
    try:
        dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_question(question: str, end_date_iso: str) -> Tuple[Optional[ParsedQuestion], str]:
    """Return (ParsedQuestion, "") or (None, reason)."""
    q = (question or "").strip()
    if not q:
        return None, "EMPTY_QUESTION"
    underlying = _detect_underlying(q)
    if underlying is None:
        return None, "UNDERLYING_UNKNOWN_OR_AMBIGUOUS"
    if _TOUCH_RE.search(q):
        return None, "BARRIER_TOUCH_MARKET_NOT_A_DIGITAL"
    end = _parse_end(end_date_iso)
    if end is None:
        return None, "END_DATE_MISSING"

    is_between = bool(_BETWEEN_RE.search(q))
    is_above = bool(_ABOVE_RE.search(q))
    is_below = bool(_BELOW_RE.search(q))
    strikes = _strikes(q)

    if is_between:
        if len(strikes) != 2:
            return None, "RANGE_STRIKES_NOT_TWO"
        lo, hi = sorted(strikes)
        kind, k_lo, k_hi = "RANGE", lo, hi
    elif is_above != is_below:  # exactly one direction word
        if len(strikes) != 1:
            return None, "STRIKE_NOT_UNIQUE"
        kind, k_lo, k_hi = ("ABOVE" if is_above else "BELOW"), strikes[0], None
    else:
        return None, "DIRECTION_UNKNOWN"

    qd = _question_date(q, end)
    if qd is not None:
        resolve = datetime(qd.year, qd.month, qd.day, 12, 0, tzinfo=ET).astimezone(timezone.utc)
        if abs((resolve - end).total_seconds()) > 36 * 3600:
            return None, "QUESTION_DATE_DISAGREES_WITH_END_DATE"
        note = "resolve=12:00 ET of question date"
    else:
        # no explicit date in the question: only trust an end date that carries a real time of day
        if end.hour == 0 and end.minute == 0 and end.second == 0:
            return None, "RESOLUTION_TIME_UNKNOWN"
        resolve = end
        note = "resolve=endDate"
    return ParsedQuestion(underlying, kind, k_lo, k_hi, resolve.astimezone(timezone.utc), note), ""


def _json_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            v = json.loads(x)
            return v if isinstance(v, list) else []
        except ValueError:
            return []
    return []


def map_gamma_market(item: Dict[str, Any]) -> Tuple[Optional[MappedMarket], Optional[RejectedMarket]]:
    mid = str(item.get("id", ""))
    q = str(item.get("question", ""))
    if item.get("closed") is True or item.get("active") is False:
        return None, RejectedMarket(mid, q, "MARKET_CLOSED_OR_INACTIVE")
    parsed, reason = parse_question(q, str(item.get("endDate", "")))
    if parsed is None:
        return None, RejectedMarket(mid, q, reason)
    tokens = [str(t) for t in _json_list(item.get("clobTokenIds"))]
    outcomes = [str(o).strip().lower() for o in _json_list(item.get("outcomes"))]
    if len(tokens) != 2 or outcomes[:2] != ["yes", "no"]:
        return None, RejectedMarket(mid, q, "NOT_A_YES_NO_BINARY_WITH_TWO_TOKENS")
    return MappedMarket(mid, q, tokens[0], tokens[1], parsed, str(item.get("description", ""))[:4000]), None


def map_gamma_markets(items: Iterable[Dict[str, Any]]) -> Tuple[List[MappedMarket], List[RejectedMarket]]:
    ok: List[MappedMarket] = []
    bad: List[RejectedMarket] = []
    seen = set()
    for it in items:
        mid = str(it.get("id", ""))
        if mid in seen:
            continue
        seen.add(mid)
        m, r = map_gamma_market(it)
        if m:
            ok.append(m)
        elif r:
            bad.append(r)
    return ok, bad
