"""Deribit implied-volatility surface -> risk-neutral digital probabilities at an arbitrary time.

Inputs are Deribit option summaries (one row per instrument):
    instrument_name  e.g. "BTC-31OCT26-110000-C"
    mark_iv          implied vol in PERCENT (52.3 means 52.3%)
    underlying_price the forward (synthetic future) of THAT expiry

Method (no extrapolation, no guessing; anything unsupported returns ``None`` with a reason):

1. Group by expiry (08:00 UTC). For each expiry build a smile in log-moneyness k = ln(K / F_e),
   using the OTM option for each strike (put below the forward, call above).
2. For the target resolution time t* strictly between two expiries t1 < t* < t2, interpolate
   TOTAL variance linearly in time at fixed log-moneyness (calendar-consistent) and the forward
   linearly in time. A target before the first listed expiry or after the last is rejected.
3. P(S_T > K) = N(d2) - F * phi(d1) * sqrt(T) * dsigma/dK  (Breeden-Litzenberger with skew),
   where dsigma/dK is a centred finite difference of the interpolated surface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from src.quant.digital_probability import digital_call_prob_analytic

SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0
_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}


def parse_instrument(name: str) -> Optional[Tuple[str, datetime, float, str]]:
    """'BTC-31OCT26-110000-C' -> ('BTC', 2026-10-31 08:00 UTC, 110000.0, 'C'). None if not a vanilla option."""
    parts = (name or "").split("-")
    if len(parts) != 4 or parts[3] not in ("C", "P"):
        return None
    ccy, exp, strike, cp = parts
    try:
        day_txt = exp[:-5]
        mon = _MONTHS[exp[-5:-2]]
        year = 2000 + int(exp[-2:])
        expiry = datetime(year, mon, int(day_txt), 8, 0, tzinfo=timezone.utc)
        return ccy, expiry, float(strike), cp
    except (KeyError, ValueError):
        return None


@dataclass(frozen=True)
class SmilePoint:
    k: float        # ln(K/F)
    iv: float       # decimal (0.52)
    strike: float


@dataclass(frozen=True)
class ExpirySmile:
    expiry: datetime
    forward: float
    points: Tuple[SmilePoint, ...]   # sorted by k


@dataclass(frozen=True)
class DigitalInputs:
    forward: float
    strike: float
    t_years: float
    sigma: float
    dsigma_dk: float
    probability: float
    expiry_lo: datetime
    expiry_hi: datetime


class DeribitSurface:
    def __init__(self, smiles: List[ExpirySmile], as_of: datetime):
        self.smiles = sorted(smiles, key=lambda s: s.expiry)
        self.as_of = as_of

    # ------------------------------------------------------------------ build
    @staticmethod
    def from_summaries(rows: Iterable[Dict], currency: str, as_of: datetime) -> "DeribitSurface":
        per_exp: Dict[datetime, Dict[float, List[Tuple[str, float, float]]]] = {}
        for r in rows:
            p = parse_instrument(str(r.get("instrument_name", "")))
            if not p or p[0] != currency:
                continue
            _, expiry, strike, cp = p
            try:
                iv = float(r.get("mark_iv"))
                fwd = float(r.get("underlying_price"))
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(iv) and math.isfinite(fwd)) or iv <= 0.0 or fwd <= 0.0 or expiry <= as_of:
                continue
            per_exp.setdefault(expiry, {}).setdefault(strike, []).append((cp, iv / 100.0, fwd))
        smiles: List[ExpirySmile] = []
        for expiry, by_strike in per_exp.items():
            fwds = [t[2] for lst in by_strike.values() for t in lst]
            fwd = sorted(fwds)[len(fwds) // 2]  # median forward across the instruments of this expiry
            pts: List[SmilePoint] = []
            for strike, lst in by_strike.items():
                want = "P" if strike < fwd else "C"      # OTM option carries the cleanest IV
                pick = next((t for t in lst if t[0] == want), lst[0])
                pts.append(SmilePoint(math.log(strike / fwd), pick[1], strike))
            pts.sort(key=lambda p: p.k)
            if len(pts) >= 4:
                smiles.append(ExpirySmile(expiry, fwd, tuple(pts)))
        return DeribitSurface(smiles, as_of)

    # ------------------------------------------------------------------ query
    @staticmethod
    def _iv_at_k(s: ExpirySmile, k: float) -> Optional[float]:
        pts = s.points
        if k < pts[0].k or k > pts[-1].k:
            return None  # no extrapolation
        for a, b in zip(pts, pts[1:]):
            if a.k <= k <= b.k:
                if b.k == a.k:
                    return a.iv
                w = (k - a.k) / (b.k - a.k)
                return a.iv + w * (b.iv - a.iv)
        return None

    def _bracket(self, target: datetime) -> Optional[Tuple[ExpirySmile, ExpirySmile]]:
        for a, b in zip(self.smiles, self.smiles[1:]):
            if a.expiry <= target <= b.expiry:
                return a, b
        return None

    def sigma_and_forward(self, target: datetime, strike: float) -> Tuple[Optional[Tuple[float, float, float]], str]:
        """Return ((sigma, forward, T_years), "") or (None, reason) at ``target`` for ``strike``."""
        t = (target - self.as_of).total_seconds()
        if t < 30 * 60:
            return None, "TOO_CLOSE_TO_RESOLUTION"
        br = self._bracket(target)
        if br is None:
            return None, "TARGET_OUTSIDE_LISTED_EXPIRIES"
        a, b = br
        ta = (a.expiry - self.as_of).total_seconds() / SECONDS_PER_YEAR
        tb = (b.expiry - self.as_of).total_seconds() / SECONDS_PER_YEAR
        tt = t / SECONDS_PER_YEAR
        if tb <= ta or ta <= 0.0:
            return None, "DEGENERATE_EXPIRY_BRACKET"
        lam = (tt - ta) / (tb - ta)
        fwd = a.forward + lam * (b.forward - a.forward)
        k = math.log(strike / fwd)
        iv_a, iv_b = self._iv_at_k(a, k), self._iv_at_k(b, k)
        if iv_a is None or iv_b is None:
            return None, "STRIKE_OUTSIDE_LISTED_SMILE"
        var = (1.0 - lam) * iv_a * iv_a * ta + lam * iv_b * iv_b * tb
        if var <= 0.0:
            return None, "NON_POSITIVE_VARIANCE"
        return (math.sqrt(var / tt), fwd, tt), ""

    def digital_above(self, target: datetime, strike: float,
                      iv_shift: float = 0.0) -> Tuple[Optional[DigitalInputs], str]:
        """P(S_T > strike). ``iv_shift`` (decimal, e.g. 0.02 = +2 vol points) is added to the interpolated
        sigma to build an uncertainty band around the fair value."""
        res, why = self.sigma_and_forward(target, strike)
        if res is None:
            return None, why
        sigma, fwd, tt = res
        sigma = max(1e-4, sigma + iv_shift)
        h = max(strike * 0.005, 1e-9)
        up, _ = self.sigma_and_forward(target, strike + h)
        dn, _ = self.sigma_and_forward(target, strike - h)
        if up is None or dn is None:
            return None, "SKEW_UNAVAILABLE_AT_SMILE_EDGE"
        dsig = (up[0] - dn[0]) / (2.0 * h)
        p = digital_call_prob_analytic(F=fwd, K=strike, sigma=sigma, dsigma_dK=dsig, T=tt)
        if not math.isfinite(p):
            return None, "NON_FINITE_PROBABILITY"
        p = min(1.0, max(0.0, p))
        br = self._bracket(target)
        return DigitalInputs(fwd, strike, tt, sigma, dsig, p, br[0].expiry, br[1].expiry), ""
