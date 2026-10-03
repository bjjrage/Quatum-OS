"""
Portfolio Allocation and Capital Budgeting Framework.

Core OS Governance Philosophy:
THE OS DOES NOT SELECT THE BEST BACKTEST.
- Strategy selection is an ensemble problem under estimation uncertainty.
- Capital allocation never picks a single "winner-take-all" strategy based on backtest metrics.
- Sizing is scaled by liquidity capacity, latency margins, and parameter uncertainty.

Evidence-Gated Invariants:
- Stages IDEA, RESEARCH, VALIDATION, HOLDOUT, PAPER, PAUSED, KILLED, ARCHIVED receive strictly $0.00 live capital.
- Stage SMALL_LIVE is strictly capped at min(small_live_cap, max_small_live_pct * equity).
- Stage ACTIVE receives risk-budgeted allocation dynamically scaled by RegimeState.
- Stage REDUCED receives 50% of ACTIVE scale.
- Total allocations never exceed available portfolio equity.
- LIVE CAPITAL LOCK: while live_capital_locked=True, authorized_live_budget == $0.0 for ALL strategies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

from src.strategies.models import StrategyStage, StrategySpec
from src.regime.policy_engine import RegimeState, StrategyRegimeState


class AllocationAction(str, Enum):
    SCALE = "SCALE"      # Increase / maintain allocation when evidence is strong and correlation low
    REDUCE = "REDUCE"    # Cut allocation (e.g. 50%) when regime shifts or decay is detected
    PAUSE = "PAUSE"      # Set allocation to $0 when conditions disfavor edge
    KILL = "KILL"        # Permanent retirement when edge is falsified or bounds violated


@dataclass
class AllocationBudget:
    strategy_id: str
    stage: StrategyStage
    base_budget_usd: float
    regime_multiplier: float
    allocated_capital_usd: float
    allocation_pct: float
    is_live_eligible: bool
    authorized_live_budget: float = 0.0
    paper_budget_usd: float = 0.0
    action: AllocationAction = AllocationAction.PAUSE
    capacity_cap_usd: float = 0.0
    uncertainty_discount: float = 1.0
    cluster_discount: float = 1.0
    latency_margin_discount: float = 1.0
    notes: str = ""


class PortfolioAllocator:
    """
    Evidence-gated capital budgeting and portfolio allocator.
    Enforces that the OS does not select the best backtest and treats portfolio construction
    as an ensemble allocation problem under uncertainty.
    """

    def __init__(
        self,
        total_equity_usd: float = 100_000.0,
        max_strategy_allocation_pct: float = 0.40,  # No single strategy gets > 40%
        small_live_absolute_cap_usd: float = 5_000.0,
        small_live_max_pct: float = 0.05,           # 5% max for SMALL_LIVE
        max_cluster_allocation_pct: float = 0.30,   # Max 30% aggregate across an EventCluster
        live_capital_locked: bool = True,
    ):
        self.total_equity_usd = total_equity_usd
        self.max_strategy_pct = max_strategy_allocation_pct
        self.small_live_cap_usd = small_live_absolute_cap_usd
        self.small_live_max_pct = small_live_max_pct
        self.max_cluster_pct = max_cluster_allocation_pct
        self.live_capital_locked = live_capital_locked

    def allocate(
        self,
        strategies: List[StrategySpec],
        regime: Optional[RegimeState] = None,
        strategy_weights: Optional[Dict[str, float]] = None,
        strategy_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
        event_clusters: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, AllocationBudget]:
        """
        Calculate capital budgets per strategy under evidence gates, multi-edge ensemble factors,
        and regime constraints.
        """
        results: Dict[str, AllocationBudget] = {}
        active_candidates: List[StrategySpec] = []

        regime_global_mult = regime.capital_allocation_multiplier if regime else 1.0

        for strat in strategies:
            strat_id = strat.strategy_id
            stage = strat.stage

            # 1. Zero capital for unvalidated, paper, paused, or killed stages
            if stage in (
                StrategyStage.IDEA,
                StrategyStage.RESEARCH,
                StrategyStage.VALIDATION,
                StrategyStage.HOLDOUT,
                StrategyStage.PAPER,
                StrategyStage.PAUSED,
                StrategyStage.KILLED,
                StrategyStage.ARCHIVED,
            ):
                action = AllocationAction.KILL if stage in (StrategyStage.KILLED, StrategyStage.ARCHIVED) else AllocationAction.PAUSE
                # Paper stages receive simulated paper budget for forward testing
                paper_sim_budget = (self.total_equity_usd * 0.10) if stage == StrategyStage.PAPER else 0.0

                results[strat_id] = AllocationBudget(
                    strategy_id=strat_id,
                    stage=stage,
                    base_budget_usd=0.0,
                    regime_multiplier=0.0,
                    allocated_capital_usd=0.0,
                    allocation_pct=0.0,
                    is_live_eligible=False,
                    authorized_live_budget=0.0,
                    paper_budget_usd=paper_sim_budget,
                    action=action,
                    notes=f"Zero capital invariant enforced for stage {stage.value}",
                )

            elif stage == StrategyStage.SMALL_LIVE:
                cap = min(self.small_live_cap_usd, self.total_equity_usd * self.small_live_max_pct)
                strat_regime_state = regime.strategy_states.get(strat_id, StrategyRegimeState.ACTIVE) if regime else StrategyRegimeState.ACTIVE
                
                if strat_regime_state == StrategyRegimeState.HALTED:
                    regime_mult = 0.0
                    action = AllocationAction.PAUSE
                elif strat_regime_state == StrategyRegimeState.REDUCED_SIZE:
                    regime_mult = 0.5
                    action = AllocationAction.REDUCE
                else:
                    regime_mult = 1.0
                    action = AllocationAction.SCALE

                final_alloc = cap * regime_mult * regime_global_mult

                results[strat_id] = AllocationBudget(
                    strategy_id=strat_id,
                    stage=stage,
                    base_budget_usd=cap,
                    regime_multiplier=regime_mult * regime_global_mult,
                    allocated_capital_usd=final_alloc,
                    allocation_pct=(final_alloc / self.total_equity_usd) if self.total_equity_usd > 0 else 0.0,
                    is_live_eligible=not self.live_capital_locked,
                    authorized_live_budget=0.0 if self.live_capital_locked else final_alloc,
                    paper_budget_usd=final_alloc,
                    action=action,
                    notes="Capped small live allocation",
                )

            elif stage in (StrategyStage.ACTIVE, StrategyStage.REDUCED):
                active_candidates.append(strat)

        # Allocate capital to ACTIVE / REDUCED strategies using multi-factor ensemble weighting
        if active_candidates:
            allocated_small = sum(r.allocated_capital_usd for r in results.values())
            remaining_equity = max(0.0, self.total_equity_usd - allocated_small)

            raw_weights: Dict[str, float] = {}
            uncertainty_discounts: Dict[str, float] = {}
            latency_discounts: Dict[str, float] = {}
            capacity_caps: Dict[str, float] = {}

            for strat in active_candidates:
                s_id = strat.strategy_id
                metrics = (strategy_metrics or {}).get(s_id, {})

                # 1. Estimation uncertainty discount (based on trial count from ExperimentRegistry)
                trials = metrics.get("trial_count", strat.trial_count if hasattr(strat, "trial_count") else 0)
                unc_discount = 1.0 / math.sqrt(1.0 + math.log(1.0 + max(0, trials)))
                uncertainty_discounts[s_id] = unc_discount

                # 2. Latency margin discount (if edge half-life close to 5s threshold)
                half_life = metrics.get("edge_half_life_s", 20.0)
                if half_life < 5.0:
                    lat_discount = 0.0
                elif half_life < 15.0:
                    lat_discount = max(0.2, (half_life - 5.0) / 10.0)
                else:
                    lat_discount = 1.0
                latency_discounts[s_id] = lat_discount

                # 3. Market depth & capacity cap (1% of 5m volume)
                vol_5m = metrics.get("avg_5m_volume_usd", float("inf"))
                cap_usd = vol_5m * 0.01 if vol_5m < float("inf") else float("inf")
                capacity_caps[s_id] = cap_usd

                # Base weight from input, halved if REDUCED stage
                w = (strategy_weights or {}).get(s_id, 1.0)
                if strat.stage == StrategyStage.REDUCED:
                    w *= 0.5

                # Modulate weight by uncertainty and latency margin
                combined_weight = w * unc_discount * lat_discount
                raw_weights[s_id] = max(0.0, combined_weight)

            total_raw_weight = sum(raw_weights.values())
            if total_raw_weight == 0.0:
                total_raw_weight = len(active_candidates)
                raw_weights = {s.strategy_id: 1.0 for s in active_candidates}

            # First pass allocation: normalize and cap at max single strategy pct
            cluster_spending: Dict[str, float] = {}
            max_cluster_usd = self.total_equity_usd * self.max_cluster_pct
            cluster_discounts: Dict[str, float] = {}

            for strat in active_candidates:
                s_id = strat.strategy_id
                norm_w = raw_weights[s_id] / total_raw_weight
                base_alloc = remaining_equity * norm_w

                # Invariant: Never exceed single-strategy cap (anti winner-take-all)
                max_single = self.total_equity_usd * self.max_strategy_pct
                base_alloc = min(base_alloc, max_single)

                # Invariant: Never exceed liquidity capacity cap
                if capacity_caps[s_id] < float("inf"):
                    base_alloc = min(base_alloc, capacity_caps[s_id])

                # Check EventCluster exposure
                c_discount = 1.0
                if event_clusters and s_id in event_clusters:
                    for clus in event_clusters[s_id]:
                        current_spent = cluster_spending.get(clus, 0.0)
                        if current_spent + base_alloc > max_cluster_usd:
                            allowed = max(0.0, max_cluster_usd - current_spent)
                            if base_alloc > 0:
                                c_discount = min(c_discount, allowed / base_alloc)
                        cluster_spending[clus] = current_spent + (base_alloc * c_discount)
                cluster_discounts[s_id] = c_discount
                base_alloc *= c_discount

                # Regime adjustment
                strat_regime_state = regime.strategy_states.get(s_id, StrategyRegimeState.ACTIVE) if regime else StrategyRegimeState.ACTIVE
                if strat_regime_state == StrategyRegimeState.HALTED:
                    strat_mult = 0.0
                    action = AllocationAction.PAUSE
                elif strat_regime_state == StrategyRegimeState.REDUCED_SIZE or strat.stage == StrategyStage.REDUCED:
                    strat_mult = 0.5
                    action = AllocationAction.REDUCE
                else:
                    strat_mult = 1.0
                    action = AllocationAction.SCALE

                effective_mult = strat_mult * regime_global_mult
                final_alloc = base_alloc * effective_mult

                results[s_id] = AllocationBudget(
                    strategy_id=s_id,
                    stage=strat.stage,
                    base_budget_usd=base_alloc,
                    regime_multiplier=effective_mult,
                    allocated_capital_usd=final_alloc,
                    allocation_pct=(final_alloc / self.total_equity_usd) if self.total_equity_usd > 0 else 0.0,
                    is_live_eligible=not self.live_capital_locked,
                    authorized_live_budget=0.0 if self.live_capital_locked else final_alloc,
                    paper_budget_usd=final_alloc,
                    action=action,
                    capacity_cap_usd=capacity_caps[s_id],
                    uncertainty_discount=uncertainty_discounts[s_id],
                    cluster_discount=cluster_discounts[s_id],
                    latency_margin_discount=latency_discounts[s_id],
                    notes=f"{strat.stage.value} risk-budgeted multi-edge allocation",
                )

        return results
