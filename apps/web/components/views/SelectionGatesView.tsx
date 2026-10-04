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
  const hasRealGates = Boolean(gates && gates.length > 0);

  // Canonical institutional gates according to hardened v1.4.2 architecture
  const gatePanels: GatePanel[] = hasRealGates ? gates : [
    {
      gate_id: "GATE_A",
      gate_name: "Latency Sensitivity & Edge Half-Life",
      gate_type: "LATENCY_SENSITIVITY",
      thresholds: {
        max_operational_delay_s: 30.0,
        min_edge_half_life_s: 5.0,
        max_delay_degradation_pct: 25.0,
      },
      threshold_is_provisional: true,
      evaluation_status: "NOT_EVALUATED",
      description: "Replays execution with simulated operational latency delays (+1s, +5s, +30s) to detect latency races and measure alpha decay half-life before promotion.",
      metrics_evaluated: ["Delay PnL Degradation", "Edge Half-Life (s)", "Latency Race Veto", "Operational Stack Budget"],
    },
    {
      gate_id: "GATE_B",
      gate_name: "Temporal Stability & Alpha Decay",
      gate_type: "TEMPORAL_STABILITY",
      thresholds: {
        min_rolling_positive_sharpe_pct: 75.0,
        max_subperiod_decay_pct: 35.0,
      },
      threshold_is_provisional: true,
      evaluation_status: "NOT_EVALUATED",
      description: "Evaluates early vs late half stability, rolling 30-day positive Sharpe ratio consistency, and flags decaying alpha profiles across historical regimes.",
      metrics_evaluated: ["Subperiod Consistency", "Rolling 30D Sharpe", "Decay Flag", "Regime Stability"],
    },
    {
      gate_id: "GATE_C",
      gate_name: "Multiple Selection Correction (DSR & FDR)",
      gate_type: "MULTIPLE_SELECTION",
      thresholds: {
        min_deflated_sharpe: 1.0,
        max_fdr_q_value: 0.05,
      },
      threshold_is_provisional: true,
      evaluation_status: "NOT_EVALUATED",
      description: "Applies Bailey & López de Prado Deflated Sharpe Ratio (DSR) and Benjamini-Hochberg False Discovery Rate (FDR) discounting nominal Sharpe across all registered trials.",
      metrics_evaluated: ["Deflated Sharpe Ratio (DSR)", "Expected Max Sharpe", "FDR q-value", "Trial Count Lineage"],
    },
    {
      gate_id: "GATE_D",
      gate_name: "Cross-Strategy Correlation & Volume Capacity",
      gate_type: "CORRELATION_CAPACITY",
      thresholds: {
        max_normal_correlation: 0.60,
        max_stress_correlation: 0.70,
        max_volume_pct: 1.0,
      },
      threshold_is_provisional: true,
      evaluation_status: "NOT_EVALUATED",
      description: "Enforces regime-conditional correlation ceilings (<0.60 normal, <0.70 stress), event cluster overlap veto, and 1% 5m volume capacity limits.",
      metrics_evaluated: ["Normal Regime Correlation", "Stress Regime Correlation", "Cluster Overlap Veto", "5m Volume Capacity"],
    },
  ];

  const getStatusBadgeVariant = (status: string): "emerald" | "rose" | "amber" | "slate" => {
    if (status === "PASS") return "emerald";
    if (status === "FAIL") return "rose";
    if (status === "PENDING") return "amber";
    return "slate";
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono-code flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-sky-600 dark:text-cyan-400" />
          Quant Strategy Selection Gates (A / B / C / D Architecture)
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 font-mono-code">
          Four invariant gatekeepers eliminating data-snooping bias, execution illusions, and latency decay before paper or live allocation.
        </p>
      </div>

      {/* MISSING EVIDENCE NOTICE */}
      {!hasRealGates && (
        <div className="rounded-lg border border-amber-300 dark:border-amber-800/80 bg-amber-50 dark:bg-amber-950/20 p-3.5 text-xs font-mono-code text-amber-900 dark:text-amber-300 flex items-center gap-2.5 shadow-sm">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <span>
            Authoritative gate evidence has not been evaluated for active strategies. Canonical A/B/C/D architecture criteria displayed below as provisional research priors.
          </span>
        </div>
      )}

      {/* PROVENANCE INVARIANT CALLOUT */}
      <div className="rounded-lg border border-sky-300 dark:border-cyan-800/80 bg-sky-50 dark:bg-[#0e1624] p-4 text-xs font-mono-code space-y-1 shadow-sm">
        <div className="flex items-center gap-2 text-sky-900 dark:text-cyan-300 font-bold uppercase">
          <ShieldCheck className="w-4 h-4" />
          Gate Evaluation Provenance Invariant
        </div>
        <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-mono-code">
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
              <Badge variant={getStatusBadgeVariant(gate.evaluation_status)} size="xs">
                {gate.evaluation_status}
              </Badge>
            </div>

            {/* Description */}
            <p className="text-xs text-slate-300 leading-relaxed font-mono-code">
              {gate.description}
            </p>

            {/* Thresholds Table */}
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-400 font-mono-code uppercase block">
                  {gate.threshold_is_provisional ? "Provisional Research Priors:" : "Deterministic Threshold Criteria:"}
                </span>
                {gate.threshold_is_provisional && (
                  <Badge variant="slate" size="xs">
                    PROVISIONAL
                  </Badge>
                )}
              </div>
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
