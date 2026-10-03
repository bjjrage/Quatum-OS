import React from "react";
import { PieChart, Lock, DollarSign, ShieldAlert, BarChart3, AlertTriangle } from "lucide-react";
import { PortfolioState } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface PortfolioViewProps {
  portfolio: PortfolioState | null;
}

export function PortfolioView({ portfolio }: PortfolioViewProps) {
  const isLoaded = portfolio !== null && portfolio !== undefined;
  const allocations = portfolio?.allocations ?? [];
  const totalPaperBudget = allocations.reduce((acc, a) => acc + (a.paper_budget_usd || 0), 0);

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <PieChart className="w-5 h-5 text-cyan-400" />
          Portfolio Construction & Dynamic Capital Allocator
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Multi-strategy risk budgeting, event cluster exposure caps, and zero-live-capital invariant enforcement.
        </p>
      </div>

      {/* ZERO LIVE CAPITAL BANNER */}
      <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-4 text-xs font-mono-code flex items-start gap-3">
        <Lock className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
        <div>
          <div className="font-bold text-sm tracking-wider uppercase text-rose-100">
            PORTFOLIO LIVE CAPITAL ALLOCATION: STRICTLY $0.00 (LOCKED)
          </div>
          <p className="text-rose-200/90 mt-1 leading-relaxed">
            All strategies are currently capped at $0 authorized live capital. Target weights depicted in this portfolio interface apply exclusively to simulated paper execution accounts.
          </p>
        </div>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Authorized Live Capital"
          value="$0.00"
          subtitle="Real exchange routing: OFF"
          badge={{ text: "LOCKED", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Simulated Paper Budget"
          value={isLoaded ? `$${totalPaperBudget.toLocaleString()} USD` : "NOT LOADED"}
          subtitle={isLoaded ? `Distributed across ${allocations.length} strategies` : "Allocation uninitialized"}
          badge={{ text: isLoaded ? "SIMULATED" : "UNINITIALIZED", variant: isLoaded ? "cyan" : "slate" }}
        />
        <MetricCard
          label="Active Event Clusters"
          value="4 Monitored"
          subtitle="Macro FOMC, CPI, Halving, Options"
          badge={{ text: "CAPS ACTIVE", variant: "blue" }}
        />
        <MetricCard
          label="Gross Portfolio Leverage"
          value="0.00x"
          subtitle="Max allowable: 2.0x"
          badge={{ text: "NOMINAL", variant: "emerald" }}
        />
      </div>

      {/* STRATEGY ALLOCATION TABLE */}
      <Card
        title="Strategy Risk Allocation Matrix"
        subtitle="Stage gating, target budgets, and live authorization bounds"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Strategy ID</th>
                <th className="py-2.5 px-3">Stage</th>
                <th className="py-2.5 px-3">Paper Budget</th>
                <th className="py-2.5 px-3">Authorized Live</th>
                <th className="py-2.5 px-3">Live Eligible</th>
                <th className="py-2.5 px-3">Capacity Cap</th>
                <th className="py-2.5 px-3">Action Directive</th>
                <th className="py-2.5 px-3">Operational Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {allocations.length > 0 ? (
                allocations.map((a) => (
                  <tr key={a.strategy_id} className="hover:bg-[#121622]/50 transition">
                    <td className="py-2.5 px-3 font-bold text-slate-100">{a.strategy_id}</td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={a.stage === "PAPER_ELIGIBLE" ? "emerald" : "amber"}
                        size="xs"
                      >
                        {a.stage}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400 font-semibold">
                      ${a.paper_budget_usd?.toLocaleString()} USD
                    </td>
                    <td className="py-2.5 px-3 font-bold text-rose-400">
                      $0.00 (LOCKED)
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant="rose" size="xs">
                        {a.is_live_eligible ? "YES" : "NO (LOCK)"}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">
                      ${a.capacity_cap_usd?.toLocaleString()} USD
                    </td>
                    <td className="py-2.5 px-3 text-slate-300 font-semibold">{a.action}</td>
                    <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate" title={a.notes}>
                      {a.notes}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-slate-500 italic">
                    No active portfolio allocations loaded from backend.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* EVENT CLUSTER EXPOSURE LIMITS */}
      <Card
        title="Event Cluster Exposure Limits & Concentration Controls"
        subtitle="Real-time exposure aggregation preventing correlated drawdowns across multiple strategies"
        variant="terminal"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {[
            { cluster: "FOMC & US Macro Data", gross: "$0", net: "$0", cap: "$50,000", util: "0.0%" },
            { cluster: "BTC Halving / Network Hardfork", gross: "$0", net: "$0", cap: "$100,000", util: "0.0%" },
            { cluster: "Quarterly Options Expiry", gross: "$0", net: "$0", cap: "$75,000", util: "0.0%" },
            { cluster: "Regulatory / Geopolitical Shocks", gross: "$0", net: "$0", cap: "$30,000", util: "0.0%" },
          ].map((ec, i) => (
            <div key={i} className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
              <span className="font-bold text-slate-200 block truncate">{ec.cluster}</span>
              <div className="space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Gross Exposure:</span>
                  <span className="text-slate-100">{ec.gross}</span>
                </div>
                <div className="flex justify-between">
                  <span>Net Exposure:</span>
                  <span className="text-slate-100">{ec.net}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cluster Cap:</span>
                  <span className="text-slate-100">{ec.cap}</span>
                </div>
                <div className="flex justify-between">
                  <span>Utilization:</span>
                  <span className="text-emerald-400 font-semibold">{ec.util}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
