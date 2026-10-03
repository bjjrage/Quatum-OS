import React, { useState, useEffect } from "react";
import { Calculator, AlertTriangle, ShieldCheck, Play, RotateCcw, BarChart2, ShieldAlert } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";
import { api } from "../../lib/api";

export function PropSimulatorView() {
  const [strategyId, setStrategyId] = useState("STR-002");
  const [providerId, setProviderId] = useState("AlphaFunding");
  const [simData, setSimData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.getPropSimulations(strategyId, providerId)
      .then((res) => {
        if (mounted) {
          setSimData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [strategyId, providerId]);

  const empiricalTradeCount = simData?.sample_size ?? 0;
  const minRequiredTrades = simData?.min_sample_size ?? 30;
  const hasSufficientData = empiricalTradeCount >= minRequiredTrades;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <Calculator className="w-5 h-5 text-cyan-400" />
            Prop Firm Exam Monte Carlo Simulator & Ruin Probability
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Empirical non-parametric bootstrap simulator enforcing strict sample size prerequisites (src/risk/capital_pockets.py).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="amber" size="sm">
            STATUS: PENDING / N = {empiricalTradeCount} / {minRequiredTrades}
          </Badge>
          <Badge variant="rose" size="sm">
            GAUSSIAN FALLBACK: BANNED
          </Badge>
        </div>
      </div>

      {/* CORE STATISTICAL INVARIANT BANNER */}
      <div className="rounded-lg border border-purple-800/80 bg-purple-950/40 p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-purple-300 font-bold uppercase">
          <ShieldAlert className="w-4 h-4 text-purple-400" />
          Empirical Bootstrap Invariant (Zero Fabricated Metrics)
        </div>
        <p className="text-slate-300 leading-relaxed">
          The simulator evaluates exam survival strictly through empirical resampling of realized trade returns.
          <strong className="text-purple-200"> A minimum of 30 empirical trades (N &ge; 30) is required.</strong> Parametric Gaussian normal distribution assumptions are strictly forbidden due to fat tails and serial correlation in liquidation cascades.
        </p>
      </div>

      {/* INSUFFICIENT DATA STATUS BANNER */}
      <div className="rounded-lg border border-amber-800/80 bg-amber-950/40 p-5 space-y-2">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-amber-100 uppercase font-mono-code">
                SIMULATOR STATUS: PENDING / INSUFFICIENT DATA (N = {empiricalTradeCount} / {minRequiredTrades})
              </span>
              <Badge variant="amber" size="xs">PREREQUISITE UNMET</Badge>
            </div>
            <p className="text-xs text-amber-200/90 mt-1 font-mono-code leading-relaxed">
              Empirical trade sample count ({empiricalTradeCount} trades) is below the institutional threshold of {minRequiredTrades} trades.
              Simulator output is locked in PENDING state. Gaussian fallback is prohibited. Realized paper broker trades must accumulate before Monte Carlo paths can be resampled.
            </p>
          </div>
        </div>
      </div>

      {/* CONTROLS BAR */}
      <Card variant="terminal">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-end">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 uppercase font-mono-code block mb-1">
              Target Strategy
            </label>
            <select
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              className="w-full px-3 py-1.5 rounded bg-[#0b0e14] border border-slate-800 text-xs font-mono-code text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="STR-002">STR-002 (Liquidity Shock v2)</option>
              <option value="STR-001">STR-001 (StatArb Mean Reversion)</option>
              <option value="STR-003">STR-003 (Funding Basis Carry)</option>
              <option value="STR-PUMP-COPY">STR-PUMP-COPY (Adversarial Meme Copy)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 uppercase font-mono-code block mb-1">
              Prop Firm Rule Profile
            </label>
            <select
              value={providerId}
              onChange={(e) => setProviderId(e.target.value)}
              className="w-full px-3 py-1.5 rounded bg-[#0b0e14] border border-slate-800 text-xs font-mono-code text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="AlphaFunding">AlphaFunding (5% Daily / 10% Trailing)</option>
              <option value="BetaTrader">BetaTrader (4% Daily / 8% Trailing)</option>
              <option value="GammaProp">GammaProp (Pending Terms Verification)</option>
            </select>
          </div>

          <div>
            <button
              disabled={true}
              className="w-full py-2 rounded text-xs font-bold font-mono-code flex items-center justify-center gap-1.5 bg-slate-800/80 text-slate-500 cursor-not-allowed border border-slate-700"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              LOCKED: REQUIRES N &ge; 30 (N = {empiricalTradeCount})
            </button>
          </div>
        </div>
      </Card>

      {/* METRIC STRIP (PENDING / UNPOPULATED) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Exam Pass Probability"
          value="—"
          subtitle="Requires N >= 30 trade samples"
          badge={{ text: "PENDING (N < 30)", variant: "amber" }}
          icon={<Calculator className="w-4 h-4" />}
        />
        <MetricCard
          label="Probability of Ruin"
          value="—"
          subtitle="Max drawdown breach model"
          badge={{ text: "PENDING (N < 30)", variant: "amber" }}
        />
        <MetricCard
          label="Median Days to Target"
          value="—"
          subtitle="Simulated path completion"
          badge={{ text: "PENDING", variant: "amber" }}
        />
        <MetricCard
          label="Empirical Trade Samples"
          value={`${empiricalTradeCount} / ${minRequiredTrades}`}
          subtitle="Minimum 30 required for MC"
          badge={{ text: "INSUFFICIENT", variant: "rose" }}
          icon={<ShieldCheck className="w-4 h-4" />}
        />
      </div>

      {/* METHODOLOGY SPECIFICATION CARD */}
      <Card
        title="Monte Carlo Architecture & Resampling Specification"
        subtitle="PropExamMonteCarloSimulator (src/risk/capital_pockets.py lines 620-720)"
        variant="terminal"
      >
        <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code text-slate-300">
          <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
            <span className="text-slate-400">Resampling Methodology:</span>
            <span className="text-cyan-400 font-semibold">Stationary Block Bootstrap (Empirical PnL vectors)</span>
          </div>
          <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
            <span className="text-slate-400">Sample Size Prerequisite:</span>
            <span className="text-amber-400 font-semibold">Strict N &ge; 30 threshold (fail-closed)</span>
          </div>
          <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
            <span className="text-slate-400">Path Iteration Count:</span>
            <span className="text-slate-200">10,000 independent simulated equity paths</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Gaussian Assumption Prohibition:</span>
            <span className="text-rose-400">STRICTLY BANNED (prevents underestimating tail ruin risk)</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
