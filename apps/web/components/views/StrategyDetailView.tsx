import React from "react";
import { ArrowLeft, ShieldCheck, AlertCircle, FileText, CheckCircle2, XCircle, Info } from "lucide-react";
import { StrategyDetail } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface StrategyDetailViewProps {
  strategy: StrategyDetail | null;
  onBack: () => void;
}

export function StrategyDetailView({ strategy, onBack }: StrategyDetailViewProps) {
  if (!strategy) {
    return (
      <div className="space-y-4">
        <button
          onClick={onBack}
          className="text-xs font-mono-code text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Strategy Registry
        </button>
        <Card variant="terminal">
          <div className="text-center py-12 text-slate-400 font-mono-code text-xs">
            Select a strategy from the registry to inspect rules, counterparty thesis, and validation logs.
          </div>
        </Card>
      </div>
    );
  }

  const thesis = strategy.counterparty_thesis;

  return (
    <div className="space-y-6">
      {/* BACK BUTTON & HEADER */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <button
          onClick={onBack}
          className="text-xs font-mono-code text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Strategy Registry
        </button>
        <div className="flex items-center gap-2">
          <Badge variant="cyan" size="sm">
            STAGE: {strategy.stage}
          </Badge>
          <Badge variant="rose" size="sm">
            LIVE: $0 LOCKED
          </Badge>
        </div>
      </div>

      {/* STRATEGY IDENTITY TITLE */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-mono-code flex items-center gap-2">
            {strategy.strategy_id}: {strategy.name}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Family: <span className="text-slate-200">{strategy.family}</span> | Version: <span className="text-slate-200">{strategy.version}</span> | Mode: <span className="text-slate-200">{strategy.execution_mode}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {strategy.economic_edge_validated ? (
            <Badge variant="emerald" size="md">
              ECONOMIC EDGE VALIDATED
            </Badge>
          ) : (
            <Badge variant="amber" size="md">
              ECONOMIC EDGE NOT VALIDATED
            </Badge>
          )}
        </div>
      </div>

      {/* ECONOMIC EDGE WARNING IF NOT VALIDATED */}
      {!strategy.economic_edge_validated && (
        <div className="rounded-lg border border-amber-800/60 bg-amber-950/30 p-4 text-xs font-mono-code text-amber-300 space-y-1">
          <div className="flex items-center gap-2 font-bold">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            ECONOMIC EDGE VERIFICATION PENDING
          </div>
          <p className="text-amber-200/80 leading-relaxed">
            This strategy has valid mathematical formulations, but its real-world economic edge is explicitly unvalidated.
            It cannot be allocated real capital until out-of-sample paper performance satisfies all four Selection Gates.
          </p>
        </div>
      )}

      {/* COUNTERPARTY THESIS PANEL */}
      <Card
        title="Counterparty Thesis (Alpha Source & Market Microstructure)"
        subtitle="Mandatory institutional justification of economic mechanism and counterparty behavior"
        variant="terminal"
      >
        {thesis ? (
          <div className="space-y-4 pt-1">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono-code">
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 text-[11px] block">Counterparty Type</span>
                <span className="text-slate-100 font-semibold mt-0.5 block">
                  {thesis.counterparty_type}
                </span>
              </div>
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 text-[11px] block">Evidence Status</span>
                <span className="text-cyan-400 font-semibold mt-0.5 block">
                  {thesis.evidence_status}
                </span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
              <div>
                <span className="text-cyan-400 font-semibold block">Economic Mechanism:</span>
                <p className="text-slate-300 mt-1 leading-relaxed">{thesis.economic_mechanism}</p>
              </div>
              <div>
                <span className="text-cyan-400 font-semibold block">Why Must Counterparty Trade Now (Inelasticity)?</span>
                <p className="text-slate-300 mt-1 leading-relaxed">{thesis.why_trade_now}</p>
              </div>
              <div>
                <span className="text-cyan-400 font-semibold block">Why Impact is Transient vs Informational:</span>
                <p className="text-slate-300 mt-1 leading-relaxed">{thesis.why_impact_may_be_transient}</p>
              </div>
            </div>

            {/* Falsification Conditions */}
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
              <span className="text-amber-400 font-semibold block uppercase">
                Empirical Falsification Criteria:
              </span>
              <ul className="list-disc list-inside space-y-1 text-slate-300">
                {thesis.falsification_conditions.map((fc, i) => (
                  <li key={i} className="text-slate-300 leading-relaxed">{fc}</li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="py-6 text-center text-xs font-mono-code text-slate-400">
            Counterparty thesis documentation not yet published for this model.
          </div>
        )}
      </Card>

      {/* RULE HIERARCHY TABLE */}
      <Card
        title="Rule Hierarchy & Evidence Chain"
        subtitle="Individual execution conditions, parameter boundaries, and empirical validation state"
        variant="terminal"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Rule ID</th>
                <th className="py-2.5 px-3">Rule Description</th>
                <th className="py-2.5 px-3">Validation Status</th>
                <th className="py-2.5 px-3">Strategy Ver</th>
                <th className="py-2.5 px-3">First Proposed</th>
                <th className="py-2.5 px-3">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {strategy.rules_evidence && strategy.rules_evidence.length > 0 ? (
                strategy.rules_evidence.map((rule) => (
                  <tr key={rule.rule_id} className="hover:bg-[#121622]/50 transition">
                    <td className="py-2.5 px-3 font-semibold text-cyan-400">{rule.rule_id}</td>
                    <td className="py-2.5 px-3 text-slate-200">{rule.description}</td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={rule.status === "ACTIVE" || rule.status === "VALIDATED" ? "emerald" : "amber"}
                        size="xs"
                      >
                        {rule.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{rule.strategy_version}</td>
                    <td className="py-2.5 px-3 text-slate-400">{rule.first_proposed_at}</td>
                    <td className="py-2.5 px-3 text-slate-400">{rule.notes}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500 font-mono-code">
                    No individual rule records mapped for this model.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
