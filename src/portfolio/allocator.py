"""
Portfolio Allocation and Capital Budgeting Framework.

Evidence-Gated Invariants:
- Stages IDEA, RESEARCH, VALIDATION, HOLDOUT, PAPER, PAUSED, KILLED, ARCHIVED receive strictly $0.00 live capital.
- Stage SMALL_LIVE is strictly capped at min(small_live_cap, max_small_live_pct * equity).
- Stage ACTIVE receives risk-budgeted allocation dynamically scaled by RegimeState.
- Stage REDUCED receives 50% of ACTIVE scale.
- Total allocations never exceed available portfolio equity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from src.strategies.models import StrategyStage, StrategySpec
from src.regime.policy_engine import RegimeState, StrategyRegimeState


@dataclass
class AllocationBudget:
    strategy_id: str
    stage: StrategyStage
    base_budget_usd: float
    regime_multiplier: float
    allocated_capital_usd: float
    allocation_pct: float
    is_live_eligible: bool
    notes: str = ""


class PortfolioAllocator:
    """
    Evidence-gated capital budgeting and portfolio allocator.
    """

    def __init__(
        self,
        total_equity_usd: float = 100_000.0,
        max_strategy_allocation_pct: float = 0.40,  # No single strategy gets > 40%
        small_live_absolute_cap_usd: float = 5_000.0,
        small_live_max_pct: float = 0.05,           # 5% max for SMALL_LIVE
        live_capital_locked: bool = True,
    ):
        self.total_equity_usd = total_equity_usd
        self.max_strategy_pct = max_strategy_allocation_pct
        self.small_live_cap_usd = small_live_absolute_cap_usd
        self.small_live_max_pct = small_live_max_pct
        self.live_capital_locked = live_capital_locked

    def allocate(
        self,
        strategies: List[StrategySpec],
        regime: Optional[RegimeState] = None,
        strategy_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, AllocationBudget]:
        """
        Calculate capital budgets per strategy under evidence gates and regime constraints.
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
                results[strat_id] = AllocationBudget(
                    strategy_id=strat_id,
                    stage=stage,
                    base_budget_usd=0.0,
                    regime_multiplier=0.0,
                    allocated_capital_usd=0.0,
                    allocation_pct=0.0,
                    is_live_eligible=False,
                    notes=f"Zero capital invariant enforced for stage {stage.value}",
                )
            elif stage == StrategyStage.SMALL_LIVE:
                # Capped incubation capital
                cap = min(self.small_live_cap_usd, self.total_equity_usd * self.small_live_max_pct)
                # Check regime
                strat_regime_state = regime.strategy_states.get(strat_id, StrategyRegimeState.ACTIVE) if regime else StrategyRegimeState.ACTIVE
                regime_mult = 0.0 if strat_regime_state == StrategyRegimeState.HALTED else (0.5 if strat_regime_state == StrategyRegimeState.REDUCED_SIZE else 1.0)
                final_alloc = cap * regime_mult * regime_global_mult

                results[strat_id] = AllocationBudget(
                    strategy_id=strat_id,
                    stage=stage,
                    base_budget_usd=cap,
                    regime_multiplier=regime_mult * regime_global_mult,
                    allocated_capital_usd=final_alloc,
                    allocation_pct=(final_alloc / self.total_equity_usd) if self.total_equity_usd > 0 else 0.0,
                    is_live_eligible=not self.live_capital_locked,
                    notes="Capped small live allocation",
                )
            elif stage in (StrategyStage.ACTIVE, StrategyStage.REDUCED):
                active_candidates.append(strat)

        # Allocate capital to ACTIVE / REDUCED strategies
        if active_candidates:
            allocated_small = sum(r.allocated_capital_usd for r in results.values())
            remaining_equity = max(0.0, self.total_equity_usd - allocated_small)

            raw_weights = {}
            for strat in active_candidates:
                w = (strategy_weights or {}).get(strat.strategy_id, 1.0)
                # If stage is REDUCED, cut weight in half
                if strat.stage == StrategyStage.REDUCED:
                    w *= 0.5
                raw_weights[strat.strategy_id] = max(0.0, w)

            total_raw_weight = sum(raw_weights.values())
            if total_raw_weight == 0.0:
                total_raw_weight = len(active_candidates)
                raw_weights = {s.strategy_id: 1.0 for s in active_candidates}

            for strat in active_candidates:
                strat_id = strat.strategy_id
                norm_w = raw_weights[strat_id] / total_raw_weight
                base_alloc = remaining_equity * norm_w

                # Cap at max single strategy pct
                max_single = self.total_equity_usd * self.max_strategy_pct
                base_alloc = min(base_alloc, max_single)

                # Regime adjustment
                strat_regime_state = regime.strategy_states.get(strat_id, StrategyRegimeState.ACTIVE) if regime else StrategyRegimeState.ACTIVE
                if strat_regime_state == StrategyRegimeState.HALTED:
                    strat_mult = 0.0
                elif strat_regime_state == StrategyRegimeState.REDUCED_SIZE:
                    strat_mult = 0.5
                else:
                    strat_mult = 1.0

                effective_mult = strat_mult * regime_global_mult
                final_alloc = base_alloc * effective_mult

                results[strat_id] = AllocationBudget(
                    strategy_id=strat_id,
                    stage=strat.stage,
                    base_budget_usd=base_alloc,
                    regime_multiplier=effective_mult,
                    allocated_capital_usd=final_alloc,
                    allocation_pct=(final_alloc / self.total_equity_usd) if self.total_equity_usd > 0 else 0.0,
                    is_live_eligible=not self.live_capital_locked,
                    notes=f"{strat.stage.value} risk-budgeted allocation",
                )

        return results
