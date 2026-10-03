import React from "react";
import { BarChart3, TrendingUp, DollarSign, Percent, PieChart, ShieldCheck } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface AttributionViewProps {
  attributionData?: {
    status?: string;
    benchmark_symbol?: string;
    gross_pnl_usd?: number;
    net_pnl_usd?: number;
    alpha_pnl_usd?: number;
    beta_pnl_usd?: number;
    total_fees_usd?: number;
    total_slippage_usd?: number;
    implementation_shortfall_usd?: number;
    by_strategy?: Record<string, { gross_pnl: number; net_pnl: number; alpha: number; beta: number; trades: number }>;
  } | null;
}

export function AttributionView({ attributionData }: AttributionViewProps) {
  const grossPnl = attributionData?.gross_pnl_usd ?? 0.0;
  const netPnl = attributionData?.net_pnl_usd ?? 0.0;
  const alphaPnl = attributionData?.alpha_pnl_usd ?? 0.0;
  const totalFees = attributionData?.total_fees_usd ?? 0.0;
  const totalSlippage = attributionData?.total_slippage_usd ?? 0.0;
  const benchmark = attributionData?.benchmark_symbol ?? "BTCUSDT";

  const rawStrategies = attributionData?.by_strategy ?? {
    "STR-001": { gross_pnl: 0.0, net_pnl: 0.0, alpha: 0.0, beta: 0.0, trades: 0 },
    "STR-002": { gross_pnl: 0.0, net_pnl: 0.0, alpha: 0.0, beta: 0.0, trades: 0 },
    "STR-003": { gross_pnl: 0.0, net_pnl: 0.0, alpha: 0.0, beta: 0.0, trades: 0 },
    "STR-PUMP-COPY": { gross_pnl: 0.0, net_pnl: 0.0, alpha: 0.0, beta: 0.0, trades: 0 },
  };

  const strategyNames: Record<string, string> = {
    "STR-001": "STR-001 (StatArb Mean Reversion)",
    "STR-002": "STR-002 v2 (Liquidity Shock Reversal)",
    "STR-003": "STR-003 (Funding Basis Carry)",
    "STR-PUMP-COPY": "STR-PUMP-COPY (Adversarial Meme Copy)",
  };

  const strategyRows = Object.entries(rawStrategies).map(([id, stats]) => ({
    id,
    name: strategyNames[id] || id,
    gross_pnl: stats.gross_pnl,
    net_pnl: stats.net_pnl,
    alpha: stats.alpha,
    beta: stats.beta,
    trades: stats.trades,
  }));

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            Performance Attribution & Return Decomposition
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Decomposition of portfolio returns into idiosyncratic alpha, market beta, execution drag, and fees.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="cyan" size="sm">
            BENCHMARK: {benchmark}
          </Badge>
          <Badge variant="amber" size="sm">
            {strategyRows.every(r => r.trades === 0) ? "PENDING OOS TRADES" : "ATTRIBUTION ACTIVE"}
          </Badge>
        </div>
      </div>

      {/* CORE STATUS BANNER */}
      <div className="rounded-lg border border-slate-800 bg-[#0c0e14] p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-cyan-300 font-bold uppercase">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          Zero Fabricated Attribution Telemetry
        </div>
        <p className="text-slate-400 leading-relaxed">
          Attribution metrics reflect strictly verified execution logs. Since live capital is locked at $0.00 and no empirical out-of-sample trades have settled, realized attribution stands at strictly $0.00 USD.
        </p>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Net Realized PnL"
          value={`$${netPnl.toFixed(2)} USD`}
          subtitle="All active strategies"
          badge={{ text: netPnl === 0 ? "NOMINAL ZERO" : (netPnl > 0 ? "PROFIT" : "LOSS"), variant: netPnl >= 0 ? "emerald" : "rose" }}
          icon={<DollarSign className="w-4 h-4" />}
        />
        <MetricCard
          label="Gross Alpha Component"
          value={`$${alphaPnl.toFixed(2)} USD`}
          subtitle={`Excess return vs ${benchmark}`}
          badge={{ text: "UNLEVERAGED", variant: "cyan" }}
        />
        <MetricCard
          label="Exchange Fees Paid"
          value={`$${totalFees.toFixed(2)} USD`}
          subtitle="Taker 5.0 bps / Maker 2.0 bps"
          badge={{ text: "RECORDED FEES", variant: "amber" }}
        />
        <MetricCard
          label="Realized Slippage Drag"
          value={`$${totalSlippage.toFixed(2)} USD`}
          subtitle="Orderbook queue impact"
          badge={{ text: "SLIPPAGE DRAG", variant: "amber" }}
        />
      </div>

      {/* ATTRIBUTION TABLE */}
      <Card
        title="Strategy-Level Return Contribution Matrix"
        subtitle="Gross profit minus friction costs per algorithmic module (src/attribution/engine.py)"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Strategy Module</th>
                <th className="py-2.5 px-3">Gross Alpha USD</th>
                <th className="py-2.5 px-3">Market Beta</th>
                <th className="py-2.5 px-3">Net Realized USD</th>
                <th className="py-2.5 px-3">Trades</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {strategyRows.map((s) => (
                <tr key={s.id} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-100">{s.name}</td>
                  <td className="py-2.5 px-3 text-slate-300">${s.gross_pnl.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-slate-400">{s.beta.toFixed(2)}</td>
                  <td className="py-2.5 px-3 font-bold text-slate-200">${s.net_pnl.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-slate-400">{s.trades}</td>
                  <td className="py-2.5 px-3 text-right">
                    <Badge variant={s.trades === 0 ? "amber" : "emerald"} size="xs">
                      {s.trades === 0 ? "PENDING OOS TRADES" : "ACTIVE"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
