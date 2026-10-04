import React, { useState } from "react";
import { TrendingUp, Sliders, AlertCircle, BarChart3, Clock, DollarSign, ShieldAlert, Cpu } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface BacktestsViewProps {
  backtestsData?: {
    status: string;
    reason?: string;
    runs: any[];
    available_strategies: string[];
    cost_models: string[];
  } | null;
}

export function BacktestsView({ backtestsData }: BacktestsViewProps) {
  const runs = backtestsData?.runs || [];
  const status = backtestsData?.status || "NOT_AVAILABLE";
  const reason = backtestsData?.reason || "Deterministic Backtest Engine available in src/backtest/engine.py; no persisted runs in active directory.";
  const availableStrategies = backtestsData?.available_strategies || ["STR-001", "STR-002", "STR-003", "STR-PUMP-COPY"];
  const costModels = backtestsData?.cost_models || ["v1_taker_5bps", "v2_maker_taker_tier1"];

  const [selectedRunId, setSelectedRunId] = useState<string>(runs.length > 0 ? runs[0].id : "");

  const current = runs.find((b: any) => b.id === selectedRunId);

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
            Rigorous Backtesting & Deflated Metric Analyzer
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Transaction-cost adjusted event-driven simulation with multiple-testing deflation and queue priority modeling.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {runs.length > 0 ? (
            runs.map((b: any) => (
              <button
                key={b.id}
                onClick={() => setSelectedRunId(b.id)}
                className={`px-3 py-1.5 rounded text-xs font-mono-code transition ${
                  selectedRunId === b.id
                    ? "bg-sky-100 text-sky-900 border border-sky-400 font-bold shadow-xs dark:bg-cyan-950 dark:text-cyan-300 dark:border-cyan-700"
                    : "bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 hover:text-slate-900 dark:bg-slate-900 dark:text-slate-400 dark:border-slate-800 dark:hover:text-slate-200"
                }`}
              >
                {b.id}
              </button>
            ))
          ) : (
            <Badge variant="amber" size="sm">
              0 PERSISTED RUNS
            </Badge>
          )}
        </div>
      </div>

      {/* CORE OS INVARIANT BANNER */}
      <div className="rounded-lg border border-cyan-800/80 bg-cyan-950/30 p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-cyan-300 font-bold uppercase">
          <ShieldAlert className="w-4 h-4 text-cyan-400" />
          OS Invariant: The OS Does Not Select the Best Backtest
        </div>
        <p className="text-slate-300 leading-relaxed">
          Capital allocation never picks a single "winner-take-all" strategy based on backtest metrics.
          All simulated returns are subjected to Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR) adjustments
          and Family-Wise Error Rate (FWER) controls to prevent p-hacking and selection bias.
        </p>
      </div>

      {/* OPERATIONAL STATUS CALLOUT */}
      <div className="rounded-lg border border-amber-800/80 bg-amber-950/30 p-4 text-xs font-mono-code space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-amber-200 uppercase">Engine Status: {status}</span>
            <Badge variant="amber" size="xs">NO PERSISTED RUNS</Badge>
          </div>
          <span className="text-[11px] text-slate-400">src/backtest/engine.py</span>
        </div>
        <p className="text-amber-300/90 leading-relaxed">
          {reason} No synthetic backtest metrics or cherry-picked curves are displayed in the Quant Cockpit.
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Deflated Sharpe Ratio (DSR)"
          value={current ? current.sharpe_deflated.toFixed(2) : "—"}
          subtitle={current ? `Nominal: ${current.sharpe_nominal.toFixed(2)}` : "Formula: Bailey & López de Prado"}
          badge={{
            text: current ? (current.sharpe_deflated >= 1.0 ? "PASSES DSR" : "FAIL DSR") : "SPECIFICATION",
            variant: current ? (current.sharpe_deflated >= 1.0 ? "emerald" : "rose") : "purple",
          }}
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <MetricCard
          label="Historical Drawdown Gate"
          value={current ? `${current.max_dd_pct.toFixed(1)}%` : "—"}
          subtitle="Max allowable: 10.0% drawdown"
          badge={{ text: "THRESHOLD: 10%", variant: "emerald" }}
        />
        <MetricCard
          label="Cost Models Configured"
          value={`${costModels.length} Models`}
          subtitle="Taker 5.0 bps / Maker 2.0 bps"
          badge={{ text: "REALISTIC FEES", variant: "cyan" }}
        />
        <MetricCard
          label="Persisted Run Count"
          value={`${runs.length} Runs`}
          subtitle="Empirical data required (N >= 30)"
          badge={{ text: runs.length === 0 ? "ZERO RUNS" : "PERSISTED", variant: runs.length === 0 ? "amber" : "emerald" }}
          icon={<Clock className="w-4 h-4" />}
        />
      </div>

      {/* SPECIFICATIONS & ENGINE DETAILS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Card
            title="Deterministic Backtest Engine Architecture"
            subtitle="src/backtest/engine.py & src/backtest/metrics.py"
            variant="terminal"
          >
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-3 text-xs font-mono-code">
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Simulation Paradigm:</span>
                <span className="text-slate-200">Deterministic event-driven execution with microsecond order lifecycle</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Supported Order Types:</span>
                <span className="text-cyan-400">LIMIT, MARKET (SimulatedOrder with queue latency)</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Cost Schedule:</span>
                <span className="text-slate-200">Maker: 2.0 bps | Taker: 5.0 bps | Base Slippage: 2.0 bps</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Multiple-Testing Correction:</span>
                <span className="text-purple-400">Deflated Sharpe Ratio (DSR) + FDR Benjamini-Hochberg</span>
              </div>
              <div className="flex justify-between items-center pt-1">
                <span className="text-slate-400">Registered Strategies:</span>
                <span className="text-slate-200">{availableStrategies.join(", ")}</span>
              </div>
            </div>
          </Card>

          <Card
            title="Out-of-Sample Performance Surface"
            subtitle="Normalized vector rendering for completed simulation runs"
            variant="terminal"
          >
            <div className="h-44 rounded bg-[#0b0e14] border border-slate-800 flex items-center justify-center p-4">
              <div className="text-center space-y-2">
                <BarChart3 className="w-8 h-8 text-slate-600 mx-auto" />
                <span className="text-xs font-mono-code text-slate-300 block">
                  No Persisted Backtest Run Loaded
                </span>
                <span className="text-[11px] font-mono-code text-slate-500 block">
                  Execute backtest run via CLI or research pipeline to generate Parquet performance artifacts.
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* SIDE PANEL: MATHEMATICAL INVARIANTS */}
        <div className="space-y-4">
          <Card
            title="Deflation Math & Selection Safeguards"
            subtitle="Bailey & López de Prado (2014) Formal Invariants"
            variant="terminal"
          >
            <div className="space-y-3 text-xs font-mono-code text-slate-300">
              <div className="p-3 rounded bg-purple-950/20 border border-purple-900/40 text-purple-300">
                <span className="font-bold block mb-1">Deflated Sharpe Equation:</span>
                DSR = PSR(SR_0), where expected maximum SR increases logarithmically with trial count K.
              </div>
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2">
                <div className="text-[11px] text-slate-400">
                  <span className="text-slate-200 font-semibold block mb-0.5">False Discovery Rate:</span>
                  Strategies must demonstrate FDR significance q &le; 0.05 across multiple parameter sweeps before admission to holdout.
                </div>
                <div className="text-[11px] text-slate-400">
                  <span className="text-slate-200 font-semibold block mb-0.5">Execution Drag Modeling:</span>
                  Deterministic engine models queue priority, spread crosses, and fill delays to avoid optimistic fill assumptions.
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
