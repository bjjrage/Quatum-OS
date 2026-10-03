import React from "react";
import { Layers, ShieldCheck, AlertTriangle, ArrowRight, BookOpen, CheckCircle, XCircle } from "lucide-react";
import { StrategySummary, NavTabId } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface StrategyRegistryViewProps {
  strategies: StrategySummary[];
  onSelectStrategy: (strategyId: string) => void;
  onNavigate: (tab: NavTabId) => void;
}

export function StrategyRegistryView({
  strategies,
  onSelectStrategy,
  onNavigate,
}: StrategyRegistryViewProps) {
  const paperEligibleCount = strategies.filter((s) => s.paper_eligibility).length;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            Strategy Catalog & Alpha Thesis Registry
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative strategy library with mandatory counterparty theses, rule hierarchies, and edge validation gates.
          </p>
        </div>
        <div>
          <button
            onClick={() => onNavigate("str002-specialized")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-50 hover:bg-amber-100 text-xs font-mono-code text-amber-900 border border-amber-300 font-semibold shadow-xs dark:bg-amber-950/60 dark:hover:bg-amber-900/60 dark:text-amber-300 dark:border-amber-800/80 transition"
          >
            Open STR-002 v2 Specialized Cockpit →
          </button>
        </div>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Registered Strategies"
          value={`${strategies.length} Strategies`}
          subtitle="4 Seed Core Quant Models"
          badge={{ text: "CATALOG READY", variant: "blue" }}
          icon={<BookOpen className="w-4 h-4" />}
        />
        <MetricCard
          label="Paper Eligible"
          value={`${paperEligibleCount} Strategies`}
          subtitle="Stage: PAPER_ELIGIBLE"
          badge={{ text: "SIMULATED", variant: "emerald" }}
        />
        <MetricCard
          label="Live Capital Authorized"
          value="$0.00"
          subtitle="Zero live capital invariant"
          badge={{ text: "LOCKED", variant: "rose" }}
        />
        <MetricCard
          label="Unvalidated Edges"
          value="1 Strategy (STR-002)"
          subtitle="Awaiting empirical live fills"
          badge={{ text: "EDGE NOT VALIDATED", variant: "amber" }}
        />
      </div>

      {/* STRATEGY CARDS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {strategies.map((strat) => {
          const isStr002 = strat.strategy_id === "STR-002";

          return (
            <Card
              key={strat.strategy_id}
              variant={isStr002 ? "warning" : "terminal"}
              className="space-y-4 hover:border-cyan-600/40 transition"
            >
              {/* Card Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-100 font-mono-code">
                      {strat.strategy_id}: {strat.name}
                    </span>
                    <Badge variant={strat.is_privileged ? "purple" : "slate"} size="xs">
                      {strat.family}
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400 mt-1 block">
                    Version: <span className="text-slate-300 font-mono-code">{strat.version}</span> | Mode: <span className="text-slate-300 font-mono-code">{strat.execution_mode}</span>
                  </span>
                </div>
                <Badge
                  variant={
                    strat.stage === "PAPER_ELIGIBLE"
                      ? "emerald"
                      : strat.stage === "PROPOSED"
                      ? "amber"
                      : "blue"
                  }
                  size="xs"
                >
                  {strat.stage}
                </Badge>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 leading-relaxed font-mono-code">
                {strat.description}
              </p>

              {/* Invariant & Edge Validation Status */}
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2 text-xs font-mono-code">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Math Foundation:</span>
                  <Badge variant={strat.math_foundation_validated ? "emerald" : "amber"} size="xs">
                    {strat.math_foundation_validated ? "VALIDATED" : "PENDING"}
                  </Badge>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Economic Edge Status:</span>
                  {strat.economic_edge_validated ? (
                    <Badge variant="emerald" size="xs">VALIDATED</Badge>
                  ) : (
                    <Badge variant="amber" size="xs">
                      {strat.economic_edge_status || "NOT VALIDATED"}
                    </Badge>
                  )}
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Live Eligibility:</span>
                  <Badge variant="rose" size="xs">
                    LOCKED ($0 AUTHORIZED)
                  </Badge>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Counterparty Thesis:</span>
                  <span className="text-slate-200">{strat.counterparty_thesis_status || "FORMULATED"}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Active Rules Count:</span>
                  <span className="text-cyan-400 font-semibold">{strat.rules_count} rules</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-1">
                {isStr002 ? (
                  <button
                    onClick={() => onNavigate("str002-specialized")}
                    className="text-xs font-mono-code text-amber-700 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 flex items-center gap-1 font-semibold"
                  >
                    Open STR-002 Specialized Cockpit →
                  </button>
                ) : (
                  <button
                    onClick={() => onSelectStrategy(strat.strategy_id)}
                    className="text-xs font-mono-code text-sky-700 dark:text-cyan-400 hover:text-sky-900 dark:hover:text-cyan-300 flex items-center gap-1 font-semibold"
                  >
                    View Strategy Details & Rules →
                  </button>
                )}
                <span className="text-[11px] text-slate-500 font-mono-code">
                  Trials: {strat.trial_count}
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
