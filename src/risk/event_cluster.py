"""
EventCluster Risk Aggregation Framework.

Aggregates risk across correlated assets, market factors, and shared event exposures
(e.g., systemic crypto sell-offs, regulatory decisions, election outcomes).
Prevents hidden leverage and correlated overconcentration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional


@dataclass
class EventCluster:
    """
    Defines an exposure cluster with deterministic exposure and stress limits.
    """
    cluster_id: str
    description: str
    max_gross_exposure_usd: float
    max_net_exposure_usd: float
    stress_loss_limit_usd: float
    stress_factor: float = 0.30  # 30% adverse shock scenario
    # Symbol -> cluster participation factor / beta (default 1.0)
    member_weights: Dict[str, float] = field(default_factory=dict)

    def is_member(self, symbol: str) -> bool:
        return symbol in self.member_weights

    def calculate_exposure(
        self,
        positions: Dict[str, float],
        mark_prices: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calculate current cluster exposure metrics.
        """
        gross_usd = 0.0
        net_usd = 0.0

        for symbol, weight in self.member_weights.items():
            qty = positions.get(symbol, 0.0)
            price = mark_prices.get(symbol, 0.0)
            if price <= 0.0 or qty == 0.0:
                continue
            position_usd = qty * price
            gross_usd += abs(position_usd) * abs(weight)
            net_usd += position_usd * weight

        # Stressed loss: worst-case adverse move given cluster stress factor
        stressed_loss_usd = gross_usd * self.stress_factor

        return {
            "gross_usd": gross_usd,
            "net_usd": net_usd,
            "stressed_loss_usd": stressed_loss_usd,
            "gross_utilization_pct": (gross_usd / self.max_gross_exposure_usd * 100.0) if self.max_gross_exposure_usd > 0 else 0.0,
            "net_utilization_pct": (abs(net_usd) / self.max_net_exposure_usd * 100.0) if self.max_net_exposure_usd > 0 else 0.0,
        }

    def check_proposed_order(
        self,
        symbol: str,
        delta_qty: float,
        price: float,
        current_positions: Dict[str, float],
        mark_prices: Dict[str, float],
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if a proposed order breaches cluster constraints.
        Returns (is_allowed, violation_reason).
        """
        if not self.is_member(symbol):
            return True, None

        weight = self.member_weights[symbol]
        curr_qty = current_positions.get(symbol, 0.0)
        new_qty = curr_qty + delta_qty

        # Simulate new positions
        simulated_positions = dict(current_positions)
        simulated_positions[symbol] = new_qty
        simulated_prices = dict(mark_prices)
        simulated_prices[symbol] = price

        new_exposure = self.calculate_exposure(simulated_positions, simulated_prices)

        if new_exposure["gross_usd"] > self.max_gross_exposure_usd:
            return False, (
                f"Cluster '{self.cluster_id}' gross exposure limit breached: "
                f"${new_exposure['gross_usd']:,.2f} > limit ${self.max_gross_exposure_usd:,.2f}"
            )

        if abs(new_exposure["net_usd"]) > self.max_net_exposure_usd:
            return False, (
                f"Cluster '{self.cluster_id}' net exposure limit breached: "
                f"${abs(new_exposure['net_usd']):,.2f} > limit ${self.max_net_exposure_usd:,.2f}"
            )

        if new_exposure["stressed_loss_usd"] > self.stress_loss_limit_usd:
            return False, (
                f"Cluster '{self.cluster_id}' stress scenario loss limit breached: "
                f"${new_exposure['stressed_loss_usd']:,.2f} > limit ${self.stress_loss_limit_usd:,.2f}"
            )

        return True, None
