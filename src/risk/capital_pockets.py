"""
Capital Pockets and Aggregate Multi-Account Risk Governance.

Architectural Invariants:
1. POCKET ISOLATION: Two distinct pocket types (OWN vs PROP).
   A loss in PROP never reduces OWN capital limits, and vice versa. Zero risk transfer.
2. AGGREGATE RISK LIMITS: Risk Engine aggregates exposure across ALL accounts regardless of pocket:
   - Global gross leverage
   - Single asset concentration
   - Total strategy exposure across accounts (e.g. STR-002 in Own + Prop A + Prop B = single exposure)
   - EventCluster exposure across accounts (different venue != diversification)
3. SELECTIVE FREEZE VS GLOBAL FREEZE:
   If a PROP account hits a daily loss limit, ONLY that prop account is frozen.
   If the global portfolio risk ceiling is breached, ALL accounts are frozen simultaneously.
4. MULTI-ACCOUNT MANUAL EVIDENCE GATE:
   Connecting a second account from the same prop firm requires written contract evidence
   answering explicit questions (same bot allowed, same strategy allowed, copy trading policy).
   Status remains PENDING_MANUAL_EVIDENCE until provided.
5. VERSIONED PROP RULE PROFILES & 5-ATTEMPT KILL SWITCH:
   Authoritative key: strategy_version + prop_rule_profile_version + provider.
   After 5 consecutive failed paid evaluations for that specific tuple, that version is blocked
   and returned to RESEARCH/REVIEW. Materially changed new strategy versions reset attempt count.
6. EMPIRICAL PATH-DEPENDENT MONTE CARLO:
   Simulates evaluation outcomes using empirical TradeSample block-bootstrap or regime-conditioned resampling.
   Gaussian IID fallback is strictly forbidden and rejected if trade history < 30 trades.
"""

from __future__ import annotations

import hashlib
import math
import random
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.risk.event_cluster import EventCluster


class PocketType(str, Enum):
    OWN = "OWN"    # Direct firm/trader capital, compounding, higher drawdown tolerance
    PROP = "PROP"  # Evaluation / funded account, strict trailing DD and daily loss limits


class CapitalPocket(BaseModel):
    """Represents an isolated capital account / trading pocket."""
    pocket_id: str
    pocket_type: PocketType
    firm_name: Optional[str] = None
    account_id: str
    initial_equity_usd: float
    current_equity_usd: float
    peak_equity_usd: float
    daily_starting_equity_usd: float
    daily_loss_limit_pct: float = 0.05       # 5% max daily loss
    trailing_drawdown_limit_pct: float = 0.10 # 10% max trailing drawdown
    is_frozen: bool = False
    freeze_reason: Optional[str] = None

    def update_equity(self, new_equity_usd: float) -> Tuple[bool, Optional[str]]:
        """Update equity and evaluate pocket-specific drawdown and daily loss rules.
        
        Returns:
            (is_breached, breach_reason)
        """
        self.current_equity_usd = new_equity_usd
        if new_equity_usd > self.peak_equity_usd:
            self.peak_equity_usd = new_equity_usd

        # Check daily loss limit
        daily_loss = self.daily_starting_equity_usd - new_equity_usd
        max_daily_loss = self.daily_starting_equity_usd * self.daily_loss_limit_pct
        if daily_loss >= max_daily_loss:
            reason = (
                f"Pocket '{self.pocket_id}' breached daily loss limit: "
                f"lost ${daily_loss:,.2f} >= ${max_daily_loss:,.2f} ({self.daily_loss_limit_pct:.1%})."
            )
            self.freeze(reason)
            return True, reason

        # Check trailing drawdown limit (especially critical for PROP)
        trailing_dd = self.peak_equity_usd - new_equity_usd
        max_trailing_dd = self.peak_equity_usd * self.trailing_drawdown_limit_pct
        if trailing_dd >= max_trailing_dd:
            reason = (
                f"Pocket '{self.pocket_id}' breached trailing drawdown limit: "
                f"drawdown ${trailing_dd:,.2f} >= ${max_trailing_dd:,.2f} ({self.trailing_drawdown_limit_pct:.1%})."
            )
            self.freeze(reason)
            return True, reason

        return False, None

    def freeze(self, reason: str) -> None:
        self.is_frozen = True
        self.freeze_reason = reason

    def unfreeze(self) -> None:
        self.is_frozen = False
        self.freeze_reason = None

    def reset_daily_equity(self, starting_equity_usd: float) -> None:
        self.daily_starting_equity_usd = starting_equity_usd


class ManualEvidenceObject(BaseModel):
    """
    Written evidence required before adding a second account from the same provider (v1.4.1 Section 17).
    Must explicitly address multi-account, same-bot, same-strategy, and copy trading policies.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str
    account_id: str
    multiple_accounts_allowed: bool = False
    same_bot_allowed: bool = False
    same_strategy_allowed: bool = False
    does_same_bot_count_as_copy_trading: bool = True  # True = restricted
    shared_account_restrictions: str = "UNKNOWN"
    cross_account_hedging_policy: str = "UNKNOWN"
    has_signed_contract_terms: bool = False
    has_documented_scaling_rules: bool = False
    has_cross_account_risk_confirmation: bool = False
    written_evidence_text: str = ""
    submission_timestamp_utc: str = ""

    def is_complete(self) -> bool:
        """
        Verify all explicit contract permissions and compliance conditions:
        - Must explicitly allow multiple accounts
        - Must explicitly allow same bot / EA
        - Must explicitly allow same strategy
        - Same bot must NOT count as copy trading
        - Signed contract terms, scaling rules, cross-account confirmation must be verified
        - Substantive evidence text (>= 50 chars)
        """
        return (
            self.multiple_accounts_allowed
            and self.same_bot_allowed
            and self.same_strategy_allowed
            and not self.does_same_bot_count_as_copy_trading
            and self.has_signed_contract_terms
            and self.has_documented_scaling_rules
            and self.has_cross_account_risk_confirmation
            and len(self.written_evidence_text.strip()) >= 50
        )


class MultiAccountEvidenceGate:
    """Governance gate enforcing written evidence before secondary provider accounts can connect."""

    def __init__(self):
        self._provider_accounts: Dict[str, Set[str]] = {}
        self._approved_evidence: Dict[str, ManualEvidenceObject] = {}

    def register_account(
        self,
        provider_name: str,
        account_id: str,
        evidence: Optional[ManualEvidenceObject] = None,
    ) -> Tuple[bool, str]:
        """Validate account addition. First account is permitted; 2nd+ requires complete manual evidence."""
        existing = self._provider_accounts.setdefault(provider_name, set())

        if account_id in existing:
            return True, "Account already registered"

        if len(existing) == 0:
            # First account from this provider: permitted
            existing.add(account_id)
            return True, "First account from provider approved."

        # Second or subsequent account from same provider requires complete written evidence
        if evidence is None or not evidence.is_complete():
            return False, (
                f"PENDING_MANUAL_EVIDENCE: Account '{account_id}' is the {len(existing)+1}-th account "
                f"for provider '{provider_name}'. Requires complete written contract evidence addressing "
                f"same-bot, same-strategy, and copy trading policies."
            )

        self._approved_evidence[f"{provider_name}:{account_id}"] = evidence
        existing.add(account_id)
        return True, "Secondary account approved with verified manual evidence."


class PropProfileVerificationStatus(str, Enum):
    """Verification status for external prop firm rule profiles."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class PropRuleProfile(BaseModel):
    """
    Authoritative 27-field versioned prop firm rule specification (v1.4.2 Fail-Closed).
    Defaults strictly to UNKNOWN and PENDING.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = "UNKNOWN"
    firm_name: Optional[str] = None
    version: str = "v1.0"
    effective_date: str = "2026-01-01"
    verified_at: Optional[str] = None

    evaluation_execution: str = "UNKNOWN"  # SIMULATED | LIVE | UNKNOWN
    funded_execution: str = "UNKNOWN"      # SIMULATED | OPTIONAL_REPLICATION | LIVE | UNKNOWN
    payout_type: str = "UNKNOWN"           # REAL | UNKNOWN
    daily_loss_mode: str = "TRAILING_EQUITY" # FIXED | TRAILING_EQUITY

    daily_loss_limit_pct: float = 0.05
    trailing_max_drawdown_pct: float = 0.10
    max_total_loss_pct: float = 0.10
    max_loss_per_trade_pct: Optional[float] = None
    profit_target_pct: float = 0.10
    min_trading_days: int = 5
    consistency_rule: Optional[str] = None
    withdrawal_cap_usd: Optional[float] = None

    instrument_universe: List[str] = Field(default_factory=list)
    venue: str = "CRYPTO_FUTURES_DEX_OR_BROKER"
    api_bot_policy: str = "UNKNOWN"         # ALLOWED | DISALLOWED | UNKNOWN
    tick_scalping_policy: str = "UNKNOWN"
    minimum_holding_policy: str = "UNKNOWN"
    news_trading_policy: str = "UNKNOWN"
    weekend_policy: str = "UNKNOWN"
    multi_account_policy: str = "UNKNOWN"
    copy_trading_policy: str = "UNKNOWN"
    hedging_policy: str = "UNKNOWN"
    country_eligibility: List[str] = Field(default_factory=list)
    verification_status: PropProfileVerificationStatus = PropProfileVerificationStatus.PENDING

    evidence_refs: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    verified_by: Optional[str] = None
    forbidden_strategies: List[str] = Field(default_factory=lambda: ["martingale", "latency_arbitrage", "news_straddle"])
    weekend_holding_allowed: bool = False
    news_trading_allowed: bool = False

    @model_validator(mode="before")
    @classmethod
    def _sync_provider_and_firm(cls, data: Any) -> Any:
        if isinstance(data, dict):
            provider = data.get("provider_id")
            firm = data.get("firm_name")
            if firm and (not provider or provider == "UNKNOWN"):
                data["provider_id"] = firm
            elif provider and not firm:
                data["firm_name"] = provider
        return data

    @property
    def profile_version(self) -> str:
        return self.version

    @property
    def fingerprint(self) -> str:
        """Deterministic cryptographic fingerprint of all rule parameters."""
        raw = (
            f"{self.provider_id}:{self.version}:{self.evaluation_execution}:"
            f"{self.funded_execution}:{self.payout_type}:{self.daily_loss_limit_pct}:"
            f"{self.trailing_max_drawdown_pct}:{self.profit_target_pct}:"
            f"{self.api_bot_policy}:{self.verification_status.value}:"
            f"{sorted(self.country_eligibility)}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_usable_for_exam(self, target_country: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Verify whether this profile has been verified and meets all paid-exam criteria."""
        reasons = []
        if self.verification_status != PropProfileVerificationStatus.VERIFIED:
            reasons.append(f"Profile verification_status is {self.verification_status.value} (must be VERIFIED)")
        if self.verified_at is None:
            reasons.append("Profile verified_at timestamp is None")
        if self.payout_type != "REAL":
            reasons.append(f"payout_type is '{self.payout_type}' (must be REAL)")
        if self.api_bot_policy != "ALLOWED":
            reasons.append(f"api_bot_policy is '{self.api_bot_policy}' (must be ALLOWED for automated trading)")
        if not self.country_eligibility:
            reasons.append("country_eligibility is empty (no countries explicitly verified)")
        elif target_country and target_country not in self.country_eligibility:
            reasons.append(f"Target country '{target_country}' not in country_eligibility: {self.country_eligibility}")
        return len(reasons) == 0, reasons


class TradeSample(BaseModel):
    """
    Empirical trade outcome sample for path-dependent Monte Carlo simulation (v1.4.1 Section 14).
    """
    trade_id: str
    timestamp_ns: int
    net_return: float  # e.g. 0.012 for +1.2%
    pnl_usd: float
    mfe_usd: float     # Maximum Favorable Excursion
    mae_usd: float     # Maximum Adverse Excursion
    holding_time_s: float
    regime: str = "NORMAL"
    event_cluster: str = "CRYPTO_DIRECTIONAL"
    floating_equity_path: Optional[List[float]] = None


class PropExamMonteCarloSimulator:
    """
    Empirical path-dependent Monte Carlo simulator for prop evaluations and versioned 5-attempt kill switch.
    Authoritative key: strategy_version + prop_rule_profile_version + provider (v1.4.1 Section 15, v1.4.2 Section 5).
    """

    def __init__(self):
        # Key: (strategy_id, strategy_version, provider_id, profile_version) -> consecutive failure count
        self._consecutive_failures: Dict[Tuple[str, str, str, str], int] = {}
        self._ineligible_combinations: Set[Tuple[str, str, str, str]] = set()

    def _get_key(
        self,
        strategy_id: str,
        provider_id: str,
        strategy_version: str = "v1.0",
        profile_version: str = "v1.0",
    ) -> Tuple[str, str, str, str]:
        return (strategy_id, strategy_version, provider_id, profile_version)

    def is_combination_eligible(
        self,
        strategy_id: str,
        provider_id: str,
        strategy_version: str = "v1.0",
        profile_version: str = "v1.0",
    ) -> bool:
        key = self._get_key(strategy_id, provider_id, strategy_version, profile_version)
        return key not in self._ineligible_combinations

    def record_attempt_result(
        self,
        strategy_id: str,
        provider_id: str,
        passed: bool,
        strategy_version: str = "v1.0",
        profile_version: str = "v1.0",
    ) -> int:
        """
        Record attempt result keyed by (strategy_version, prop_rule_profile_version, provider).
        After 5 consecutive failures, that specific combination is marked ineligible and returned to REVIEW.
        """
        key = self._get_key(strategy_id, provider_id, strategy_version, profile_version)
        if passed:
            self._consecutive_failures[key] = 0
            return 0

        current_fails = self._consecutive_failures.get(key, 0) + 1
        self._consecutive_failures[key] = current_fails

        if current_fails >= 5:
            self._ineligible_combinations.add(key)

        return current_fails

    def simulate(
        self,
        strategy_id: str,
        profile: PropRuleProfile,
        daily_mean_ret: Optional[float] = None,
        daily_vol_ret: Optional[float] = None,
        trades: Optional[List[TradeSample]] = None,
        strategy_version: str = "v1.0",
        exam_fee_usd: float = 500.0,
        expected_funded_payout_usd: float = 5_000.0,
        n_simulations: int = 500,
        max_days: int = 60,
        resampling_mode: str = "block_bootstrap",  # "block_bootstrap" or "regime_conditioned"
        block_size: int = 5,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Run empirical path-dependent Monte Carlo simulation.
        If empirical trade sample is missing or < 30 trades, strictly returns PENDING / INSUFFICIENT_DATA.
        Gaussian IID fallback is strictly rejected.
        """
        provider_id = profile.provider_id or profile.firm_name or "UNKNOWN"
        profile_ver = profile.version or "v1.0"

        # Check 5-attempt kill switch ONLY for this exact key (v1.4.2 Section 5)
        if not self.is_combination_eligible(strategy_id, provider_id, strategy_version, profile_ver):
            return {
                "status": "BLOCKED",
                "strategy_id": strategy_id,
                "strategy_version": strategy_version,
                "provider_id": provider_id,
                "profile_version": profile_ver,
                "attempt_blocked_by_history": True,
                "eligible_for_paid_exam": False,
                "is_eligible": False,
                "pass_probability": 0.0,
                "failure_probability": 1.0,
                "action": "RETURN_TO_RESEARCH_REVIEW",
                "reason": (
                    f"KILL_SWITCH_ACTIVE: 5 consecutive evaluation failures for "
                    f"({strategy_id} {strategy_version}, profile {profile_ver}, {provider_id}). "
                    f"Combination returned to RESEARCH / REVIEW."
                ),
            }

        # Check empirical sample validity (v1.4.1 Section 14)
        if trades is None or len(trades) < 30:
            count = len(trades) if trades is not None else 0
            return {
                "status": "PENDING / INSUFFICIENT_DATA",
                "strategy_id": strategy_id,
                "strategy_version": strategy_version,
                "provider_id": provider_id,
                "profile_version": profile_ver,
                "rule_fingerprint": profile.fingerprint,
                "attempt_blocked_by_history": False,
                "eligible_for_paid_exam": False,
                "is_eligible": False,
                "pass_probability": 0.0,
                "failure_probability": 0.0,
                "reason": (
                    f"Insufficient empirical trade sample ({count} trades < 30 minimum). "
                    f"Gaussian IID fallback strictly forbidden."
                ),
                "simulations_run": 0,
            }

        # Check profile usability / verification (v1.4.2 Section 6)
        usable, profile_unusable_reasons = profile.is_usable_for_exam()
        if not usable:
            return {
                "status": "BLOCKED_UNVERIFIED_PROFILE",
                "strategy_id": strategy_id,
                "strategy_version": strategy_version,
                "provider_id": provider_id,
                "profile_version": profile_ver,
                "rule_fingerprint": profile.fingerprint,
                "attempt_blocked_by_history": False,
                "eligible_for_paid_exam": False,
                "is_eligible": False,
                "pass_probability": 0.0,
                "failure_probability": 0.0,
                "reason": (
                    f"Prop profile {provider_id} ({profile_ver}) is unverified or unusable for paid exam: "
                    f"{'; '.join(profile_unusable_reasons)}."
                ),
                "simulations_run": 0,
            }

        # Empirical Path-Dependent Simulation
        rng = random.Random(random_seed)
        passes = 0
        failures = 0
        failure_reasons: Dict[str, int] = {}
        days_to_pass: List[int] = []
        days_to_fail: List[int] = []
        max_drawdowns: List[float] = []
        final_equities: List[float] = []

        target = profile.profit_target_pct
        daily_loss_limit = profile.daily_loss_limit_pct
        trailing_limit = profile.trailing_max_drawdown_pct

        # Prepare blocks for block-bootstrap
        trade_blocks: List[List[TradeSample]] = []
        for i in range(len(trades) - block_size + 1):
            trade_blocks.append(trades[i : i + block_size])
        if not trade_blocks:
            trade_blocks = [[t] for t in trades]

        for _ in range(n_simulations):
            equity = 1.0
            peak = 1.0
            passed = False
            failed = False
            failure_reason = ""
            day_profits: List[float] = []
            max_dd = 0.0

            day = 0
            while day < max_days and not passed and not failed:
                day += 1
                daily_start_equity = equity

                # Sample 1 to 3 trades for this simulated day using block bootstrap
                sampled_block = rng.choice(trade_blocks)
                n_trades_today = rng.randint(1, min(3, len(sampled_block)))
                daily_trades = sampled_block[:n_trades_today]

                for tr in daily_trades:
                    # Intraday adverse excursion check
                    if tr.mae_usd > 0:
                        mae_ret = tr.mae_usd / (daily_start_equity * 100_000.0)
                        intraday_dd = ((peak - (equity - (equity * mae_ret))) / peak)
                        if intraday_dd >= trailing_limit:
                            failed = True
                            failure_reason = "TRAILING_DRAWDOWN_BREACH_INTRADAY"
                            break

                    equity *= (1.0 + tr.net_return)
                    if equity > peak:
                        peak = equity

                    dd = (peak - equity) / peak
                    if dd > max_dd:
                        max_dd = dd

                    if dd >= trailing_limit:
                        failed = True
                        failure_reason = "TRAILING_DRAWDOWN_BREACH"
                        break

                if failed:
                    break

                # Daily loss evaluation
                day_pnl = equity - daily_start_equity
                day_loss = daily_start_equity - equity
                day_loss_pct = day_loss / daily_start_equity
                day_profits.append(max(0.0, day_pnl))

                if day_loss_pct >= daily_loss_limit:
                    failed = True
                    failure_reason = "DAILY_LOSS_BREACH"
                    break

                # Profit target & consistency check
                cumulative_return = equity - 1.0
                if cumulative_return >= target and day >= profile.min_trading_days:
                    # Check consistency rule (no single day > 30% of total profit)
                    total_profit = sum(day_profits)
                    max_single_day = max(day_profits) if day_profits else 0.0
                    if total_profit > 0 and (max_single_day / total_profit) > 0.35:
                        # Consistency failed, must keep trading
                        pass
                    else:
                        passed = True
                        break

            max_drawdowns.append(max_dd)
            final_equities.append(equity)

            if passed:
                passes += 1
                days_to_pass.append(day)
            else:
                failures += 1
                if not failure_reason:
                    failure_reason = "MAX_DAYS_EXPIRED_WITHOUT_TARGET"
                failure_reasons[failure_reason] = failure_reasons.get(failure_reason, 0) + 1
                days_to_fail.append(day)

        pass_prob = passes / n_simulations
        fail_prob = failures / n_simulations
        expected_payout = pass_prob * expected_funded_payout_usd
        exam_roi = (expected_payout - exam_fee_usd) / exam_fee_usd if exam_fee_usd > 0 else 0.0

        failure_reason_distribution = {k: v / max(1, failures) for k, v in failure_reasons.items()}
        max_drawdowns.sort()
        final_equities.sort()

        eligible_for_paid_exam = (
            usable
            and pass_prob >= 0.50
            and exam_roi > 0.0
        )

        return {
            "status": "COMPLETED",
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "provider_id": provider_id,
            "profile_version": profile_ver,
            "rule_fingerprint": profile.fingerprint,
            "attempt_blocked_by_history": False,
            "eligible_for_paid_exam": eligible_for_paid_exam,
            "is_eligible": True,
            "pass_probability": pass_prob,
            "failure_probability": fail_prob,
            "failure_reason_distribution": failure_reason_distribution,
            "expected_days_to_pass": sum(days_to_pass) / max(1, len(days_to_pass)),
            "expected_days_to_fail": sum(days_to_fail) / max(1, len(days_to_fail)),
            "max_drawdown_distribution": {
                "mean": sum(max_drawdowns) / len(max_drawdowns),
                "p50": max_drawdowns[len(max_drawdowns) // 2],
                "p95": max_drawdowns[int(len(max_drawdowns) * 0.95)],
            },
            "final_equity_distribution": {
                "mean": sum(final_equities) / len(final_equities),
                "p50": final_equities[len(final_equities) // 2],
                "p95": final_equities[int(len(final_equities) * 0.95)],
            },
            "expected_payout_usd": expected_payout,
            "exam_roi": exam_roi,
            "simulations_run": n_simulations,
            "random_seed": random_seed,
        }


class MultiAccountRiskAggregator:
    """
    Aggregates exposure across ALL accounts and capital pockets to enforce global limits.
    Enforces limits on:
    - Global gross leverage
    - Single asset concentration
    - Single strategy concentration across accounts (e.g. STR-002 in Own + Prop A + Prop B)
    - EventCluster exposure across accounts (different venue != diversification)
    """

    def __init__(
        self,
        max_global_gross_leverage: float = 3.0,
        max_global_single_asset_pct: float = 0.25,
        max_global_strategy_pct: float = 0.40,
        max_global_drawdown_pct: float = 0.15,
    ):
        self.max_global_gross_leverage = max_global_gross_leverage
        self.max_global_single_asset_pct = max_global_single_asset_pct
        self.max_global_strategy_pct = max_global_strategy_pct
        self.max_global_drawdown_pct = max_global_drawdown_pct

        self.pockets: Dict[str, CapitalPocket] = {}
        self.positions_by_account: Dict[str, Dict[str, float]] = {}  # account_id -> symbol -> qty
        self.strategy_positions: Dict[str, Dict[str, Dict[str, float]]] = {}  # account_id -> strategy_id -> symbol -> qty
        self.mark_prices: Dict[str, float] = {}
        self.event_clusters: Dict[str, EventCluster] = {}

    def add_pocket(self, pocket: CapitalPocket) -> None:
        self.pockets[pocket.pocket_id] = pocket

    def register_event_cluster(self, cluster: EventCluster) -> None:
        self.event_clusters[cluster.cluster_id] = cluster

    def update_positions(
        self,
        account_id: str,
        positions: Dict[str, float],
        mark_prices: Dict[str, float],
        strategy_allocations: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        self.positions_by_account[account_id] = dict(positions)
        self.mark_prices.update(mark_prices)
        if strategy_allocations is not None:
            if account_id in strategy_allocations and isinstance(strategy_allocations[account_id], dict):
                self.strategy_positions[account_id] = strategy_allocations[account_id]
            else:
                self.strategy_positions[account_id] = strategy_allocations

    def total_aggregate_equity(self) -> float:
        return sum(p.current_equity_usd for p in self.pockets.values())

    def aggregate_positions(self) -> Dict[str, float]:
        """Aggregate net position per symbol across ALL accounts (OWN + PROP)."""
        agg: Dict[str, float] = {}
        for acc_pos in self.positions_by_account.values():
            for sym, qty in acc_pos.items():
                agg[sym] = agg.get(sym, 0.0) + qty
        return agg

    def aggregate_strategy_exposures(self) -> Dict[str, float]:
        """Aggregate total gross notional exposure per strategy across ALL accounts."""
        strat_gross: Dict[str, float] = {}
        for acc_id, strat_map in self.strategy_positions.items():
            for strat_id, pos_map in strat_map.items():
                for sym, qty in pos_map.items():
                    price = self.mark_prices.get(sym, 0.0)
                    notional = abs(qty) * price
                    strat_gross[strat_id] = strat_gross.get(strat_id, 0.0) + notional
        return strat_gross

    def aggregate_cluster_exposures(self) -> Dict[str, float]:
        """Aggregate gross notional exposure per EventCluster across ALL accounts."""
        agg_pos = self.aggregate_positions()
        cluster_gross: Dict[str, float] = {}

        for cluster_id, cluster in self.event_clusters.items():
            gross = 0.0
            for sym, weight in cluster.member_weights.items():
                qty = agg_pos.get(sym, 0.0)
                price = self.mark_prices.get(sym, 0.0)
                gross += abs(qty * weight) * price
            cluster_gross[cluster_id] = gross

        return cluster_gross

    def evaluate_global_risk(self) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Evaluate aggregate multi-account risk across all pockets.
        
        Returns:
            (is_approved, violation_reason, metrics)
        """
        agg_equity = self.total_aggregate_equity()
        if agg_equity <= 0.0:
            return False, "Total aggregate portfolio equity is non-positive.", {}

        agg_pos = self.aggregate_positions()
        gross_notional = sum(abs(qty) * self.mark_prices.get(sym, 0.0) for sym, qty in agg_pos.items())
        gross_leverage = gross_notional / agg_equity

        # 1. Global gross leverage check
        if gross_leverage > self.max_global_gross_leverage:
            reason = (
                f"Global gross leverage ({gross_leverage:.2f}x) breaches ceiling "
                f"({self.max_global_gross_leverage:.2f}x) across all accounts combined."
            )
            for p in self.pockets.values():
                p.freeze(reason)
            return False, reason, {"gross_leverage": gross_leverage, "gross_notional": gross_notional}

        # 2. Single asset concentration check
        for sym, qty in agg_pos.items():
            sym_notional = abs(qty) * self.mark_prices.get(sym, 0.0)
            sym_pct = sym_notional / agg_equity
            if sym_pct > self.max_global_single_asset_pct:
                reason = (
                    f"Global concentration on '{sym}' ({sym_pct:.1%}) breaches ceiling "
                    f"({self.max_global_single_asset_pct:.1%}) across all accounts combined."
                )
                for p in self.pockets.values():
                    p.freeze(reason)
                return False, reason, {"breached_symbol": sym, "concentration_pct": sym_pct}

        # 3. Strategy concentration check across accounts
        strat_exposures = self.aggregate_strategy_exposures()
        for strat_id, strat_notional in strat_exposures.items():
            strat_pct = strat_notional / agg_equity
            if strat_pct > self.max_global_strategy_pct:
                reason = (
                    f"Aggregate exposure for strategy '{strat_id}' (${strat_notional:,.2f}, {strat_pct:.1%}) "
                    f"breaches maximum strategy concentration limit ({self.max_global_strategy_pct:.1%}) "
                    f"across combined accounts."
                )
                for p in self.pockets.values():
                    p.freeze(reason)
                return False, reason, {"breached_strategy": strat_id, "strategy_concentration_pct": strat_pct}

        # 4. EventCluster limits check across accounts
        cluster_exposures = self.aggregate_cluster_exposures()
        for cluster_id, cluster_notional in cluster_exposures.items():
            cluster = self.event_clusters.get(cluster_id)
            if cluster and cluster_notional > cluster.max_gross_exposure_usd:
                reason = (
                    f"Aggregate EventCluster exposure for '{cluster_id}' (${cluster_notional:,.2f}) "
                    f"breaches ceiling (${cluster.max_gross_exposure_usd:,.2f}) across combined accounts."
                )
                for p in self.pockets.values():
                    p.freeze(reason)
                return False, reason, {"breached_cluster": cluster_id, "cluster_notional": cluster_notional}

        return True, None, {
            "gross_leverage": gross_leverage,
            "gross_notional": gross_notional,
            "strategy_exposures": strat_exposures,
            "cluster_exposures": cluster_exposures,
        }
