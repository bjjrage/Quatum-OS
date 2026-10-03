import React from "react";
import { ShieldCheck, Clock, Zap, BarChart2, AlertCircle, CheckCircle } from "lucide-react";
import { GatePanel } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface SelectionGatesViewProps {
  gates: GatePanel[];
  provenanceInvariant?: string;
}

export function SelectionGatesView({ gates, provenanceInvariant }: SelectionGatesViewProps) {
  // Default institutional gates if empty
  const gatePanels: GatePanel[] = gates && gates.length > 0 ? gates : [
    {
      gate_id: "GATE_A",
      gate_name: "Statistical Significance & Multiple Testing Deflation",
      gate_type: "STATISTICAL",
      thresholds: {
        min_deflated_sharpe: 1.0,
        max_p_value: 0.05,
        min_trade_count: 50,
      },
      threshold_is_provisional: false,
      evaluation_status: "ACTIVE_EVALUATION",
      description: "Applies Bailey-Lopez de Prado Deflated Sharpe Ratio (DSR) discounting nominal Sharpe for total number of evaluated model variations.",
      metrics_evaluated: ["Nominal Sharpe", "Number of Trials", "Skewness", "Kurtosis", "DSR Score"],
    },
    {
      gate_id: "GATE_B",
      gate_name: "Latency Sensitivity & Alpha Decay Half-Life",
      gate_type: "MICROSTRUCTURE",
      thresholds: {
        latency_p50_ms: 15.0,
        latency_p95_ms: 30.0,
        latency_p99_ms: 50.0,
        min_alpha_half_life_ms: 500.0,
      },
      threshold_is_provisional: false,
      evaluation_status: "ACTIVE_EVALUATION",
      description: "Evaluates profitability decay when simulated order arrival is delayed by P50, P95, and P99 latency percentiles.",
      metrics_evaluated: ["Alpha Half-Life (ms)", "P95 Latency Degradation", "Queue Priority Loss"],
    },
    {
      gate_id: "GATE_C",
      gate_name: "Execution Realism & Adverse Selection",
      gate_type: "EXECUTION",
      thresholds: {
        base_slippage_bps: 2.5,
        taker_fee_bps: 5.0,
        adverse_selection_buffer_bps: 1.5,
      },
      threshold_is_provisional: false,
      evaluation_status: "ACTIVE_EVALUATION",
      description: "Enforces non-zero taker fees, orderbook depth exhaustion, and adverse selection on passive limit fills.",
      metrics_evaluated: ["Net Profit Factor", "Slippage-to-Spread Ratio", "Post-Fill Drift"],
    },
    {
      gate_id: "GATE_D",
      gate_name: "Parameter Stability & Cross-Regime Robustness",
      gate_type: "ROBUSTNESS",
      thresholds: {
        max_parameter_sensitivity_curvature: 0.25,
        min_regime_consistency_pct: 75.0,
        max_drawdown_limit_pct: 10.0,
      },
      threshold_is_provisional: false,
      evaluation_status: "ACTIVE_EVALUATION",
      description: "Tests local neighborhood parameter perturbations (+-10%, +-20%) to guarantee performance is not an overfitted knife-edge.",
      metrics_evaluated: ["Neighborhood Sharpness", "Macro Regime Survival", "Drawdown Under Stress"],
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-cyan-400" />
          Quant Strategy Selection Gates (A / B / C / D Architecture)
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Four invariant gatekeepers eliminating data-snooping bias, execution illusions, and latency decay before paper or live allocation.
        </p>
      </div>

      {/* PROVENANCE INVARIANT CALLOUT */}
      <div className="rounded-lg border border-cyan-800/80 bg-[#0e1624] p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-cyan-300 font-bold uppercase">
          <ShieldCheck className="w-4 h-4" />
          Gate Evaluation Provenance Invariant
        </div>
        <p className="text-slate-300 leading-relaxed">
          {provenanceInvariant ||
            "Gate rules and execution thresholds are mathematically identical across backtest evaluation, paper trading monitoring, and capital allocation. No strategy may bypass any gate through manual operator override."}
        </p>
      </div>

      {/* GATES GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {gatePanels.map((gate) => (
          <Card
            key={gate.gate_id}
            variant="terminal"
            className="space-y-4 hover:border-cyan-600/50 transition"
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-bold text-cyan-400 font-mono-code uppercase block">
                  [{gate.gate_id}] {gate.gate_type}
                </span>
                <h3 className="text-sm font-semibold text-slate-100 font-mono-code mt-0.5">
                  {gate.gate_name}
                </h3>
              </div>
              <Badge variant="amber" size="xs">
                {gate.evaluation_status}
              </Badge>
            </div>

            {/* Description */}
            <p className="text-xs text-slate-300 leading-relaxed font-mono-code">
              {gate.description}
            </p>

            {/* Thresholds Table */}
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 font-mono-code uppercase block">
                Deterministic Threshold Criteria:
              </span>
              <div className="space-y-1.5 text-xs font-mono-code">
                {Object.entries(gate.thresholds).map(([param, val]) => (
                  <div key={param} className="flex justify-between text-slate-300">
                    <span className="text-slate-400">{param}:</span>
                    <span className="font-bold text-slate-100">
                      {typeof val === "number" ? val.toString() : JSON.stringify(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Evaluated Metrics */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {gate.metrics_evaluated.map((m, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono-code text-slate-400"
                >
                  {m}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
