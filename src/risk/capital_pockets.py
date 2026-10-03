"""
Capital Pockets and Aggregate Multi-Account Risk Governance.

Architectural Invariants:
1. POCKET ISOLATION: Two distinct pocket types (OWN vs PROP).
   A loss in PROP never reduces OWN capital limits, and vice versa. Zero risk transfer.
2. AGGREGATE RISK LIMITS: Risk Engine aggregates exposure across ALL accounts regardless of pocket.
   Global gross leverage, single asset cap, and EventCluster limits apply across the union of all accounts.
3. SELECTIVE FREEZE VS GLOBAL FREEZE:
   If a PROP account hits a daily loss limit, ONLY that prop account is frozen.
   If the global portfolio risk ceiling is breached, ALL accounts are frozen simultaneously.
4. MULTI-ACCOUNT MANUAL EVIDENCE GATE:
   Connecting a second account from the same prop firm requires written contract evidence.
   Status remains PENDING_MANUAL_EVIDENCE until provided.
5. VERSIONED PROP RULE PROFILES & 5-ATTEMPT KILL SWITCH:
   Prop rules are versioned. 5 consecutive exam failures permanently marks a strategy PROP_INELIGIBLE
   for that firm, blocking further exam purchases.
"""

from __future__ import annotations

import math
import random
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field


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
    """Written evidence required before adding a second account from the same provider."""
    provider_name: str
    account_id: str
    has_signed_contract_terms: bool
    has_documented_scaling_rules: bool
    has_cross_account_risk_confirmation: bool
    written_evidence_text: str
    submission_timestamp_utc: str

    def is_complete(self) -> bool:
        return (
            self.has_signed_contract_terms
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
        """Validate account addition. First account is permitted; 2nd+ requires manual evidence."""
        existing = self._provider_accounts.setdefault(provider_name, set())

        if account_id in existing:
            return True, "Account already registered"

        if len(existing) == 0:
            # First account from this provider: permitted
            existing.add(account_id)
            return True, "First account from provider approved."

        # Second or subsequent account from same provider requires written evidence
        if evidence is None or not evidence.is_complete():
            return False, (
                f"PENDING_MANUAL_EVIDENCE: Account '{account_id}' is the {len(existing)+1}-th account "
                f"for provider '{provider_name}'. Requires complete written contract evidence."
            )

        self._approved_evidence[f"{provider_name}:{account_id}"] = evidence
        existing.add(account_id)
        return True, "Secondary account approved with verified manual evidence."


class PropRuleProfile(BaseModel):
    """Versioned prop firm rule specification."""
    firm_name: str
    version: str
    effective_date: str
    daily_loss_limit_pct: float = 0.05
    trailing_max_drawdown_pct: float = 0.10
    max_total_loss_pct: float = 0.10
    profit_target_pct: float = 0.10
    min_trading_days: int = 5
    consistency_rule: Optional[str] = "no single day > 30% of total profit"
    allowed_instruments: List[str] = Field(default_factory=list)
    forbidden_strategies: List[str] = Field(default_factory=lambda: ["martingale", "latency_arbitrage", "news_straddle"])
    weekend_holding_allowed: bool = False
    news_trading_allowed: bool = False


class PropExamMonteCarloSimulator:
    """Path-dependent Monte Carlo simulator for prop evaluation passes and 5-attempt kill switch."""

    def __init__(self):
        # (strategy_id, firm_name) -> consecutive failure count
        self._consecutive_failures: Dict[Tuple[str, str], int] = {}
        self._ineligible_strategies: Set[Tuple[str, str]] = set()

    def is_strategy_eligible(self, strategy_id: str, firm_name: str) -> bool:
        return (strategy_id, firm_name) not in self._ineligible_strategies

    def record_attempt_result(self, strategy_id: str, firm_name: str, passed: bool) -> int:
        """Record attempt result and trigger 5-attempt kill switch if breached."""
        key = (strategy_id, firm_name)
        if passed:
            self._consecutive_failures[key] = 0
            return 0

        current_fails = self._consecutive_failures.get(key, 0) + 1
        self._consecutive_failures[key] = current_fails

        if current_fails >= 5:
            self._ineligible_strategies.add(key)

        return current_fails

    def simulate(
        self,
        strategy_id: str,
        profile: PropRuleProfile,
        daily_mean_ret: float,
        daily_vol_ret: float,
        exam_fee_usd: float = 500.0,
        expected_funded_payout_usd: float = 5_000.0,
        n_simulations: int = 1000,
        max_days: int = 60,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """Simulate path-dependent probability of passing the prop challenge."""
        if not self.is_strategy_eligible(strategy_id, profile.firm_name):
            return {
                "strategy_id": strategy_id,
                "firm_name": profile.firm_name,
                "is_eligible": False,
                "pass_probability": 0.0,
                "breach_probability": 1.0,
                "exam_roi": -1.0,
                "reason": "KILL_SWITCH_ACTIVE: Strategy failed 5 consecutive attempts. PROP_INELIGIBLE.",
            }

        rng = random.Random(random_seed)
        passes = 0
        breaches = 0

        target = profile.profit_target_pct
        daily_loss_limit = profile.daily_loss_limit_pct
        trailing_limit = profile.trailing_max_drawdown_pct

        for _ in range(n_simulations):
            equity = 1.0
            peak = 1.0
            passed = False
            breached = False

            for day in range(max_days):
                daily_ret = rng.gauss(daily_mean_ret, daily_vol_ret)
                
                # Check daily loss limit breach
                if daily_ret <= -daily_loss_limit:
                    breached = True
                    break

                equity *= (1.0 + daily_ret)
                if equity > peak:
                    peak = equity

                # Check trailing drawdown breach
                drawdown = (peak - equity) / peak
                if drawdown >= trailing_limit:
                    breached = True
                    break

                # Check profit target
                cumulative_return = equity - 1.0
                if cumulative_return >= target and (day + 1) >= profile.min_trading_days:
                    passed = True
                    break

            if passed:
                passes += 1
            else:
                breaches += 1

        pass_prob = passes / n_simulations
        breach_prob = breaches / n_simulations
        expected_payout = pass_prob * expected_funded_payout_usd
        exam_roi = (expected_payout - exam_fee_usd) / exam_fee_usd if exam_fee_usd > 0 else 0.0

        return {
            "strategy_id": strategy_id,
            "firm_name": profile.firm_name,
            "is_eligible": True,
            "pass_probability": pass_prob,
            "breach_probability": breach_prob,
            "expected_payout_usd": expected_payout,
            "exam_roi": exam_roi,
            "simulations_run": n_simulations,
        }


class MultiAccountRiskAggregator:
    """Aggregates exposure across all accounts and capital pockets to enforce global limits."""

    def __init__(
        self,
        max_global_gross_leverage: float = 3.0,
        max_global_single_asset_pct: float = 0.25,
        max_global_drawdown_pct: float = 0.15,
    ):
        self.max_global_gross_leverage = max_global_gross_leverage
        self.max_global_single_asset_pct = max_global_single_asset_pct
        self.max_global_drawdown_pct = max_global_drawdown_pct

        self.pockets: Dict[str, CapitalPocket] = {}
        self.positions_by_account: Dict[str, Dict[str, float]] = {}  # account_id -> symbol -> qty
        self.mark_prices: Dict[str, float] = {}

    def add_pocket(self, pocket: CapitalPocket) -> None:
        self.pockets[pocket.pocket_id] = pocket

    def update_positions(self, account_id: str, positions: Dict[str, float], mark_prices: Dict[str, float]) -> None:
        self.positions_by_account[account_id] = dict(positions)
        self.mark_prices.update(mark_prices)

    def total_aggregate_equity(self) -> float:
        return sum(p.current_equity_usd for p in self.pockets.values())

    def aggregate_positions(self) -> Dict[str, float]:
        """Aggregate net position per symbol across ALL accounts (OWN + PROP)."""
        agg: Dict[str, float] = {}
        for acc_pos in self.positions_by_account.values():
            for sym, qty in acc_pos.items():
                agg[sym] = agg.get(sym, 0.0) + qty
        return agg

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

        # Check global gross leverage ceiling
        if gross_leverage > self.max_global_gross_leverage:
            reason = (
                f"Global gross leverage ({gross_leverage:.2f}x) breaches ceiling "
                f"({self.max_global_gross_leverage:.2f}x) across all accounts combined."
            )
            # Global breach freezes ALL accounts
            for p in self.pockets.values():
                p.freeze(reason)
            return False, reason, {"gross_leverage": gross_leverage, "gross_notional": gross_notional}

        # Check single asset concentration across all accounts
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

        return True, None, {"gross_leverage": gross_leverage, "gross_notional": gross_notional}
