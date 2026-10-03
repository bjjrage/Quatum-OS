"""STR-002: Behavioral Alpha / Impulse-Overshoot-Retracement Event Study & Strategy Engine.

CAUSAL EXECUTION MODEL (Hardening 02C)
--------------------------------------
Timeline invariants:
    event_timestamp <= signal_timestamp <= decision_timestamp
    entry_timestamp >= decision_timestamp + execution_latency
The event peak price is event METADATA, never an executable fill.

LONG-only executable side:
    ENTRY  = first point-in-time BBO with timestamp >= decision + latency, filled at ASK.
    EXIT   = first BBO with timestamp >= entry_timestamp + horizon (within a documented
             tolerance), filled at BID. Never mid, never the last row, never an index.
    STOP   = chronological; fills at the BID of the triggering quote (conservative: a gap
             through the stop gives the gapped bid, not the theoretical stop price).

Economic result (per fixed horizon, no "best" horizon selection):
    gross_return_bps = (exit_bid / entry_ask - 1) * 1e4        (spread is embedded here)
    total_cost_bps   = entry_fee_bps + exit_fee_bps + slippage_bps   (MODEL_ASSUMPTION)
    net_return_bps   = gross_return_bps - total_cost_bps
Spread is NOT added again to total_cost_bps. The spread components are informational.

MFE / MAE / max retracement are POST_HOC_DIAGNOSTIC only and never feed any return.
SHORT (mean reversion after EXPANSION_UP) is RESEARCH ONLY and never leaves this module
as an executable Signal.
"""
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Any, List, Optional

from .factory import CandidateHypothesis, Signal, SignalDirection
from .models import StrategySpec, StrategyFamily, StrategyOrigin, StrategyStage
from src.research.events import PriceImpulseEvent, ShockDirection

NS_PER_S = 1_000_000_000
NS_PER_MS = 1_000_000

# Canonical fixed horizons (seconds)
CANONICAL_HORIZONS_S: Dict[str, int] = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800}

STRATEGY_VERSION = "event_study_v2c"

STATUS_EXECUTED = "EXECUTED"
STATUS_STOPPED = "STOPPED"
STATUS_HORIZON_NOT_AVAILABLE = "HORIZON_NOT_AVAILABLE"
STATUS_MISSING_ASK = "UNEXECUTABLE_MISSING_ASK"
STATUS_MISSING_BID = "UNEXECUTABLE_MISSING_BID"
STATUS_RESEARCH_ONLY_SHORT = "RESEARCH_ONLY_SHORT_NOT_EXECUTABLE"
STATUS_ENTRY_OK = "ENTRY_FILLED"


class MoveClassification(str, Enum):
    FORCED_LIQUIDITY_MOVE = "FORCED_LIQUIDITY_MOVE"
    INFORMATIVE_MOVE = "INFORMATIVE_MOVE"


@dataclass(frozen=True)
class BboQuote:
    """Point-in-time best bid/offer record."""
    timestamp_ns: int
    bid: Optional[float]
    ask: Optional[float]
    bid_depth: Optional[float] = None
    ask_depth: Optional[float] = None


def _valid_price(p: Optional[float]) -> bool:
    return p is not None and math.isfinite(p) and p > 0.0


@dataclass
class EntryExecution:
    status: str
    decision_timestamp_ns: int
    entry_target_timestamp_ns: int
    execution_latency_ms: float
    entry_timestamp_ns: Optional[int] = None
    entry_ask: Optional[float] = None
    entry_bid: Optional[float] = None
    entry_price_source: str = "NONE"
    entry_spread_bps: Optional[float] = None
    entry_spread_component_bps: Optional[float] = None  # (ask - mid)/mid, informational
    ask_depth: Optional[float] = None
    capacity_status: str = "UNEXECUTABLE"
    fill_ratio: Optional[float] = None


@dataclass
class HorizonResult:
    horizon: str
    status: str
    target_timestamp_ns: Optional[int] = None
    exit_timestamp_ns: Optional[int] = None
    exit_bid: Optional[float] = None
    exit_price_source: str = "NONE"
    exit_spread_component_bps: Optional[float] = None  # (mid - bid)/mid, informational
    gross_return_bps: Optional[float] = None
    entry_fee_bps: Optional[float] = None
    exit_fee_bps: Optional[float] = None
    slippage_bps: Optional[float] = None
    total_cost_bps: Optional[float] = None
    net_return_bps: Optional[float] = None
    cost_assumption_label: str = "MODEL_ASSUMPTION"


@dataclass
class PostHocDiagnostics:
    """Retrospective best-path information. NEVER used for returns, exits or admission."""
    label: str = "POST_HOC_DIAGNOSTIC"
    mfe: Optional[float] = None
    mae: Optional[float] = None
    max_retracement_ratio: Optional[float] = None
    time_to_retracement_s: Optional[float] = None


@dataclass
class EventProvenance:
    strategy_id: str = "STR-002"
    strategy_version: str = STRATEGY_VERSION
    beta_down: Optional[float] = None
    beta_up: Optional[float] = None
    gamma_eth: Optional[float] = None
    residual: Optional[float] = None
    shock_z_score: Optional[float] = None
    btc_state: str = "UNKNOWN"
    dataset_version_or_hash: str = "UNKNOWN"
    git_sha: str = "UNKNOWN"


@dataclass
class EventStudyObservation:
    """Audit-friendly record: event metadata, signal metadata, entry, diagnostics, horizons."""
    # event metadata
    event_id: str
    symbol: str
    venue: str
    classification: MoveClassification
    direction: str
    impulse_magnitude: float
    prior_realized_volatility: float
    forced_liquidation_volume: float
    # point-in-time telemetry (None / UNKNOWN when not supplied; never fabricated)
    funding_rate: Optional[float]
    open_interest_delta: Optional[float]
    market_regime: str
    liquidity_tier: str
    spread_bps: Optional[float]
    depth: Optional[float]
    # causal timeline
    event_timestamp_ns: int
    signal_timestamp_ns: int
    decision_timestamp_ns: int
    entry_timestamp_ns: Optional[int]
    # execution
    execution_side: str
    entry: EntryExecution
    stop_price: Optional[float]
    risk_distance: Optional[float]
    stop_fill_model: str
    horizon_results: Dict[str, HorizonResult]
    post_hoc_diagnostics: PostHocDiagnostics
    provenance: EventProvenance


class STR002EventStudyAlpha(CandidateHypothesis):
    """STR-002 candidate strategy evaluating impulse overshoot and short-horizon retracement."""

    def __init__(
        self,
        min_z_score: float = 2.5,
        min_retracement_target_pct: float = 0.35,  # ex-ante signal threshold assumption
        fee_and_slippage_bps: float = 8.0,
        execution_latency_ms: float = 250.0,
        entry_fee_bps: float = 2.0,   # MODEL_ASSUMPTION
        exit_fee_bps: float = 2.0,    # MODEL_ASSUMPTION
        slippage_bps: float = 4.0,    # MODEL_ASSUMPTION
        horizon_tolerance_s: float = 60.0,
    ):
        for name, v in (
            ("execution_latency_ms", execution_latency_ms),
            ("entry_fee_bps", entry_fee_bps),
            ("exit_fee_bps", exit_fee_bps),
            ("slippage_bps", slippage_bps),
            ("horizon_tolerance_s", horizon_tolerance_s),
        ):
            if v is None or not math.isfinite(v) or v < 0.0:
                raise ValueError(f"{name} must be finite and >= 0, got {v!r}")
        spec = StrategySpec(
            strategy_id="STR-002",
            family=StrategyFamily.BEHAVIORAL,
            origin=StrategyOrigin.HUMAN,
            stage=StrategyStage.RESEARCH,
            name="Behavioral Alpha / Short-Horizon Retracement",
            description="Exploitation of mechanical overshoot and subsequent mean reversion from forced liquidation cascades",
            parameters={
                "min_z_score": min_z_score,
                "min_retracement_target_pct": min_retracement_target_pct,
                "fee_and_slippage_bps": fee_and_slippage_bps,
                "execution_latency_ms": execution_latency_ms,
                "entry_fee_bps": entry_fee_bps,
                "exit_fee_bps": exit_fee_bps,
                "slippage_bps": slippage_bps,
                "horizon_tolerance_s": horizon_tolerance_s,
            },
        )
        super().__init__(spec)
        self.min_z = min_z_score
        self.min_target = min_retracement_target_pct
        self.hurdle_bps = fee_and_slippage_bps  # ex-ante signal hurdle only
        self.execution_latency_ms = float(execution_latency_ms)
        self.entry_fee_bps = float(entry_fee_bps)
        self.exit_fee_bps = float(exit_fee_bps)
        self.slippage_bps = float(slippage_bps)
        self.horizon_tolerance_ns = int(horizon_tolerance_s * NS_PER_S)
        # Non-executable SHORT research evidence (never emitted as Signal)
        self.research_candidates: List[Dict[str, Any]] = []

    @staticmethod
    def classify_move(
        has_forced_liquidations: bool,
        liquidation_volume: float,
        is_fundamental_news: bool = False,
    ) -> MoveClassification:
        """Distinguish Informative Moves (hacks, delistings, material news) from Forced/Liquidity Moves."""
        if is_fundamental_news:
            return MoveClassification.INFORMATIVE_MOVE
        if has_forced_liquidations or liquidation_volume > 100_000.0:
            return MoveClassification.FORCED_LIQUIDITY_MOVE
        return MoveClassification.INFORMATIVE_MOVE

    @staticmethod
    def classify_capacity(ask_depth: Optional[float], order_qty: Optional[float]) -> (str, Optional[float]):
        """Return (capacity_status, fill_ratio). Never assumes infinite liquidity."""
        if ask_depth is None or not math.isfinite(ask_depth):
            return "DEPTH_NOT_AVAILABLE", None
        if ask_depth <= 0.0:
            return "UNEXECUTABLE", 0.0
        if order_qty is None or not math.isfinite(order_qty) or order_qty <= 0.0:
            return "CAPACITY_UNRESOLVED_NO_ORDER_SIZE", None
        ratio = min(1.0, ask_depth / order_qty)
        if ratio >= 1.0:
            return "FULL_FILL", 1.0
        if ratio >= 0.5:
            return "PARTIAL_FILL", ratio
        return "CAPACITY_LIMITED", ratio

    def analyze_event_trajectory(
        self,
        event: PriceImpulseEvent,
        bbo_series: List[BboQuote],
        signal_timestamp_ns: Optional[int] = None,
        decision_timestamp_ns: Optional[int] = None,
        provenance: Optional[EventProvenance] = None,
        order_qty: Optional[float] = None,
        is_fundamental_news: bool = False,
        funding_rate: Optional[float] = None,
        oi_delta: Optional[float] = None,
        market_regime: str = "UNKNOWN",
        liquidity_tier: str = "UNKNOWN",
        stop_buffer_pct: float = 0.005,
        horizons_s: Optional[Dict[str, int]] = None,
    ) -> EventStudyObservation:
        """Build a causal observation from the event and a point-in-time BBO series."""
        horizons = horizons_s if horizons_s is not None else CANONICAL_HORIZONS_S
        classification = self.classify_move(
            has_forced_liquidations=event.has_forced_liquidations,
            liquidation_volume=event.forced_liquidation_volume,
            is_fundamental_news=is_fundamental_news,
        )

        event_ts = event.ts_peak_ns
        signal_ts = signal_timestamp_ns if signal_timestamp_ns is not None else event_ts
        decision_ts = decision_timestamp_ns if decision_timestamp_ns is not None else signal_ts
        if not (event_ts <= signal_ts <= decision_ts):
            raise ValueError("Causal timeline violated: require event <= signal <= decision")

        for i in range(1, len(bbo_series)):
            if bbo_series[i].timestamp_ns < bbo_series[i - 1].timestamp_ns:
                raise ValueError("BBO series must be time-ordered")

        latency_ns = int(self.execution_latency_ms * NS_PER_MS)
        entry_target = decision_ts + latency_ns
        prov = provenance if provenance is not None else EventProvenance()
        is_short_research = event.direction == ShockDirection.EXPANSION_UP

        def _build(entry: EntryExecution, results, stop_price, risk_dist, stop_model, posthoc):
            return EventStudyObservation(
                event_id=event.event_id,
                symbol=event.symbol,
                venue=event.venue,
                classification=classification,
                direction=event.direction.value if hasattr(event.direction, "value") else str(event.direction),
                impulse_magnitude=round(event.impulse_return, 6),
                prior_realized_volatility=round(event.prior_volatility, 6),
                forced_liquidation_volume=event.forced_liquidation_volume,
                funding_rate=funding_rate,
                open_interest_delta=oi_delta,
                market_regime=market_regime,
                liquidity_tier=liquidity_tier,
                spread_bps=entry.entry_spread_bps,
                depth=entry.ask_depth,
                event_timestamp_ns=event_ts,
                signal_timestamp_ns=signal_ts,
                decision_timestamp_ns=decision_ts,
                entry_timestamp_ns=entry.entry_timestamp_ns,
                execution_side="SHORT_RESEARCH_ONLY" if is_short_research else "LONG",
                entry=entry,
                stop_price=stop_price,
                risk_distance=risk_dist,
                stop_fill_model=stop_model,
                horizon_results=results,
                post_hoc_diagnostics=posthoc,
                provenance=prov,
            )

        # SHORT is research-only: no executable fills are modeled at all.
        if is_short_research:
            entry = EntryExecution(
                status=STATUS_RESEARCH_ONLY_SHORT,
                decision_timestamp_ns=decision_ts,
                entry_target_timestamp_ns=entry_target,
                execution_latency_ms=self.execution_latency_ms,
            )
            return _build(entry, {}, None, None, "NOT_APPLICABLE", PostHocDiagnostics())

        # ---- ENTRY: first quote at/after decision + latency, filled at ASK ----
        entry_quote = next((q for q in bbo_series if q.timestamp_ns >= entry_target), None)
        if entry_quote is None or not _valid_price(entry_quote.ask):
            entry = EntryExecution(
                status=STATUS_MISSING_ASK,
                decision_timestamp_ns=decision_ts,
                entry_target_timestamp_ns=entry_target,
                execution_latency_ms=self.execution_latency_ms,
                entry_timestamp_ns=entry_quote.timestamp_ns if entry_quote else None,
            )
            results = {
                h: HorizonResult(horizon=h, status=STATUS_MISSING_ASK) for h in horizons
            }
            return _build(entry, results, None, None, "NOT_APPLICABLE", PostHocDiagnostics())

        entry_ask = float(entry_quote.ask)
        entry_ts = entry_quote.timestamp_ns
        entry_bid = float(entry_quote.bid) if _valid_price(entry_quote.bid) else None
        spread_bps = None
        entry_spread_comp = None
        if entry_bid is not None and entry_ask >= entry_bid:
            mid = 0.5 * (entry_ask + entry_bid)
            spread_bps = (entry_ask - entry_bid) / mid * 1e4
            entry_spread_comp = (entry_ask - mid) / mid * 1e4
        cap_status, fill_ratio = self.classify_capacity(entry_quote.ask_depth, order_qty)
        entry = EntryExecution(
            status=STATUS_ENTRY_OK,
            decision_timestamp_ns=decision_ts,
            entry_target_timestamp_ns=entry_target,
            execution_latency_ms=self.execution_latency_ms,
            entry_timestamp_ns=entry_ts,
            entry_ask=entry_ask,
            entry_bid=entry_bid,
            entry_price_source="ASK",
            entry_spread_bps=spread_bps,
            entry_spread_component_bps=entry_spread_comp,
            ask_depth=entry_quote.ask_depth,
            capacity_status=cap_status,
            fill_ratio=fill_ratio,
        )

        # ---- STOP (set from the actual entry ask; evaluated chronologically) ----
        abs_impulse = abs(event.peak_price - event.start_price)
        stop_dist = max(entry_ask * stop_buffer_pct, 0.10 * abs_impulse)
        stop_dist = min(stop_dist, entry_ask * 0.99)
        stop_price = entry_ask - stop_dist
        stop_ts: Optional[int] = None
        stop_fill_bid: Optional[float] = None
        for q in bbo_series:
            if q.timestamp_ns <= entry_ts:
                continue
            if _valid_price(q.bid) and q.bid <= stop_price:
                stop_ts = q.timestamp_ns
                stop_fill_bid = float(q.bid)  # conservative: gapped bid, not theoretical stop
                break

        # ---- FIXED HORIZONS (timestamp based) ----
        results: Dict[str, HorizonResult] = {}
        for name, secs in horizons.items():
            target = entry_ts + int(secs * NS_PER_S)
            res = HorizonResult(horizon=name, status=STATUS_HORIZON_NOT_AVAILABLE, target_timestamp_ns=target)
            if stop_ts is not None and stop_ts <= target:
                self._fill_exit(res, entry_ask, stop_fill_bid, stop_ts, None, STATUS_STOPPED, "BID_STOP_TRIGGER_QUOTE")
                results[name] = res
                continue
            hq = next((q for q in bbo_series if q.timestamp_ns >= target), None)
            if hq is None or hq.timestamp_ns > target + self.horizon_tolerance_ns:
                results[name] = res  # HORIZON_NOT_AVAILABLE; no substitution
                continue
            if not _valid_price(hq.bid):
                res.status = STATUS_MISSING_BID
                res.exit_timestamp_ns = hq.timestamp_ns
                results[name] = res
                continue
            self._fill_exit(res, entry_ask, float(hq.bid), hq.timestamp_ns, hq.ask, STATUS_EXECUTED, "BID")
            results[name] = res

        # ---- POST-HOC DIAGNOSTICS (never feed returns) ----
        mfe = 0.0
        mae = 0.0
        max_ret = 0.0
        t_ret = 0.0
        for q in bbo_series:
            if q.timestamp_ns <= entry_ts or not _valid_price(q.bid):
                continue
            favorable = q.bid - event.peak_price
            adverse = event.peak_price - q.bid
            mfe = max(mfe, favorable)
            mae = max(mae, adverse)
            if abs_impulse > 1e-9:
                ratio = favorable / abs_impulse
                if ratio > max_ret:
                    max_ret = ratio
                    t_ret = (q.timestamp_ns - event_ts) / NS_PER_S
        posthoc = PostHocDiagnostics(
            mfe=round(mfe, 6),
            mae=round(mae, 6),
            max_retracement_ratio=round(max_ret, 6),
            time_to_retracement_s=round(t_ret, 3),
        )
        return _build(entry, results, stop_price, stop_dist, "BID_AT_TRIGGER_QUOTE_CONSERVATIVE", posthoc)

    def _fill_exit(
        self,
        res: HorizonResult,
        entry_ask: float,
        exit_bid: float,
        exit_ts: int,
        exit_ask: Optional[float],
        status: str,
        source: str,
    ) -> None:
        res.status = status
        res.exit_timestamp_ns = exit_ts
        res.exit_bid = exit_bid
        res.exit_price_source = source
        if _valid_price(exit_ask) and exit_ask >= exit_bid:
            exit_mid = 0.5 * (exit_ask + exit_bid)
            res.exit_spread_component_bps = (exit_mid - exit_bid) / exit_mid * 1e4
        res.gross_return_bps = (exit_bid / entry_ask - 1.0) * 1e4
        res.entry_fee_bps = self.entry_fee_bps
        res.exit_fee_bps = self.exit_fee_bps
        res.slippage_bps = self.slippage_bps
        res.total_cost_bps = self.entry_fee_bps + self.exit_fee_bps + self.slippage_bps
        res.net_return_bps = res.gross_return_bps - res.total_cost_bps

    def generate_signal(self, market_data: Dict[str, Any], current_ts_ns: int) -> Optional[Signal]:
        """Generate a LONG mean-reversion signal only on qualified Forced Liquidity moves.

        The SHORT hypothesis (after EXPANSION_UP) is research-only: it is recorded in
        `research_candidates` and NEVER returned through the executable Signal interface.
        """
        event: Optional[PriceImpulseEvent] = market_data.get("impulse_event")
        if not event or abs(event.z_score) < self.min_z:
            return None

        classification = self.classify_move(
            has_forced_liquidations=event.has_forced_liquidations,
            liquidation_volume=event.forced_liquidation_volume,
            is_fundamental_news=market_data.get("is_fundamental_news", False),
        )

        # INFORMATIVE MOVES HAVE NO OBLIGATION TO REVERT -> STRICT FILTER
        if classification == MoveClassification.INFORMATIVE_MOVE:
            return None

        expected_retrace_bps = abs(event.impulse_return) * self.min_target * 10000.0
        net_edge = expected_retrace_bps - self.hurdle_bps  # ex-ante threshold only

        if net_edge <= 0.0:
            return None

        if event.direction == ShockDirection.EXPANSION_UP:
            self.research_candidates.append({
                "event_id": event.event_id,
                "symbol": event.symbol,
                "venue": event.venue,
                "hypothesis": "SHORT_MEAN_REVERSION",
                "status": "RESEARCH_ONLY",
                "is_executable": False,
                "ts_ns": current_ts_ns,
            })
            return None

        confidence = min(1.0, net_edge / 50.0)
        target_weight = min(0.15, net_edge / 200.0)

        return Signal(
            strategy_id=self.spec.strategy_id,
            symbol=event.symbol,
            venue=event.venue,
            direction=SignalDirection.LONG,
            target_weight=round(target_weight, 4),
            confidence=round(confidence, 4),
            expected_edge_bps=round(net_edge, 2),
            ts_ns=current_ts_ns,
            metadata={
                "classification": classification.value,
                "impulse_z_score": event.z_score,
                "impulse_return_bps": round(event.impulse_return * 10000.0, 1),
                "expected_retracement_bps": round(expected_retrace_bps, 1),
                "forced_liq_volume": event.forced_liquidation_volume,
                "expected_edge_label": "EX_ANTE_THRESHOLD_ASSUMPTION",
            },
        )
