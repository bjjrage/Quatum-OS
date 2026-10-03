import React from "react";
import { BarChart3, TrendingUp, DollarSign, Percent, PieChart } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

export function AttributionView() {
  const strategyAttribution = [
    { strategy: "STR-002 (Liquidity Shock v2)", gross_pnl: 1845.0, fees: 312.0, slippage: 142.5, net_pnl: 1390.5, share_pct: 68.2 },
    { strategy: "STR-001 (StatArb Mean Reversion)", gross_pnl: 840.0, fees: 280.0, slippage: 110.0, net_pnl: 450.0, share_pct: 22.1 },
    { strategy: "STR-003 (Funding Basis Carry)", gross_pnl: 280.0, fees: 64.0, slippage: 18.0, net_pnl: 198.0, share_pct: 9.7 },
    { strategy: "STR-004 (Vol Skew Mispricing)", gross_pnl: 0.0, fees: 0.0, slippage: 0.0, net_pnl: 0.0, share_pct: 0.0 },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          Quant Performance Attribution & Friction Decomposition
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Decomposition of returns into pure alpha, market beta, execution drag, and exchange liquidity fees.
        </p>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Simulated Net PnL"
          value="+$2,038.50 USD"
          subtitle="All active paper models"
          badge={{ text: "NET PROFIT", variant: "emerald" }}
          icon={<DollarSign className="w-4 h-4" />}
        />
        <MetricCard
          label="Gross Alpha Component"
          value="+$2,965.00 USD"
          subtitle="Pre-friction theoretical edge"
          badge={{ text: "GROSS EDGE", variant: "cyan" }}
        />
        <MetricCard
          label="Exchange Fees Paid"
          value="-$656.00 USD"
          subtitle="Taker 5.0 bps / Maker 2.0 bps"
          badge={{ text: "FEES", variant: "amber" }}
        />
        <MetricCard
          label="Realized Slippage Drag"
          value="-$270.50 USD"
          subtitle="Orderbook queue impact"
          badge={{ text: "SLIPPAGE", variant: "amber" }}
        />
      </div>

      {/* ATTRIBUTION TABLE */}
      <Card
        title="Strategy-Level Return Contribution Matrix"
        subtitle="Gross profit minus friction costs per algorithmic module"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Strategy Module</th>
                <th className="py-2.5 px-3">Gross Alpha USD</th>
                <th className="py-2.5 px-3">Exchange Fees</th>
                <th className="py-2.5 px-3">Slippage Cost</th>
                <th className="py-2.5 px-3">Net Realized USD</th>
                <th className="py-2.5 px-3 text-right">Contribution %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {strategyAttribution.map((s, i) => (
                <tr key={i} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-100">{s.strategy}</td>
                  <td className="py-2.5 px-3 text-cyan-400">+${s.gross_pnl.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-rose-400">-${s.fees.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-amber-400">-${s.slippage.toFixed(2)}</td>
                  <td className="py-2.5 px-3 font-bold text-emerald-400">+${s.net_pnl.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-right font-bold text-slate-200">{s.share_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
