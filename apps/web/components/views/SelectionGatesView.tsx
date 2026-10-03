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
      gate_id: "A",
      gate_name: "Gate A: Latency Sensitivity",
      gate_type: "LATENCY_SENSITIVITY",
      thresholds: {
        max_sharpe_drop_pct_at_5s: 0.50,
        min_edge_half_life_s: 5.0,
        latency_safety_margin_multiplier: 2.0,
      },
      threshold_is_provisional: true,
      evaluation_status: "PENDING",
      description: "Replays backtest across simulated execution latencies (+1s, +5s, +30s). Rejects LATENCY_RACE strategies.",
      metrics_evaluated: ["p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "edge_half_life_s", "break_even_latency_s", "latency_safety_margin"],
    },
    {
      gate_id: "B",
      gate_name: "Gate B: Temporal Stability & Alpha Decay",
      gate_type: "TEMPORAL_STABILITY",
      thresholds: {
        min_decay_ratio: 0.50,
        min_positive_rolling_pct: 0.75,
      },
      threshold_is_provisional: true,
      evaluation_status: "PENDING",
      description: "Validates that returns do not concentrate in early training periods. Checks rolling 30-day positive consistency.",
      metrics_evaluated: ["first_half_sharpe", "second_half_sharpe", "decay_ratio", "pct_positive_rolling"],
    },
    {
      gate_id: "C",
      gate_name: "Gate C: Multiple Selection Correction",
      gate_type: "MULTIPLE_SELECTION",
      thresholds: {
        min_dsr: 0.50,
        max_adjusted_pvalue: 0.05,
      },
      threshold_is_provisional: true,
      evaluation_status: "PENDING",
      description: "Bailey & López de Prado Deflated Sharpe Ratio (DSR) and Benjamini-Hochberg False Discovery Rate (FDR).",
      metrics_evaluated: ["dsr", "expected_max_null_sharpe", "adjusted_p_value", "trial_count"],
    },
    {
      gate_id: "D",
      gate_name: "Gate D: Correlation & Capacity",
      gate_type: "CORRELATION_CAPACITY",
      thresholds: {
        max_normal_correlation: 0.60,
        max_stress_correlation: 0.70,
        max_capacity_volume_pct: 0.01,
      },
      threshold_is_provisional: true,
      evaluation_status: "PENDING",
      description: "Cross-strategy correlation under normal and stressed regimes, EventCluster overlap, and 1% 5m volume capacity.",
      metrics_evaluated: ["max_normal_correlation", "max_stress_correlation", "proposed_allocation_usd", "capacity_ceiling_usd"],
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
