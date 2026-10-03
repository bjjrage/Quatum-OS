import React, { useState } from "react";
import { FlaskConical, Filter, AlertTriangle, CheckCircle, Search, GitBranch } from "lucide-react";
import { ExperimentRecord } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface ExperimentsViewProps {
  experiments: ExperimentRecord[];
  strategyTrialCounts?: Record<string, number>;
}

export function ExperimentsView({ experiments, strategyTrialCounts = {} }: ExperimentsViewProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");

  const filtered = experiments.filter((e) => {
    const matchesStrat = selectedStrategy === "ALL" || e.strategy_id === selectedStrategy;
    const matchesSearch =
      e.experiment_id.toLowerCase().includes(search.toLowerCase()) ||
      e.git_sha.toLowerCase().includes(search.toLowerCase()) ||
      (e.entry_model && e.entry_model.toLowerCase().includes(search.toLowerCase()));
    return matchesStrat && matchesSearch;
  });

  const passedCount = experiments.filter((e) => e.gate_result === "PASS").length;
  const failedCount = experiments.filter((e) => e.gate_result === "FAIL" || e.gate_result === "REJECTED").length;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-cyan-400" />
          Quant Research Experiment Registry & Falsification Tracker
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Cryptographically hashed trial provenance, parameter space tracking, and gate falsification audit log.
        </p>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Experiments Logged"
          value={`${experiments.length} Runs`}
          subtitle="Cryptographically tracked"
          badge={{ text: "AUDITED", variant: "cyan" }}
          icon={<FlaskConical className="w-4 h-4" />}
        />
        <MetricCard
          label="Gate Passed"
          value={`${passedCount} Runs`}
          subtitle="Qualified for paper evaluation"
          badge={{ text: "VALID", variant: "emerald" }}
        />
        <MetricCard
          label="Falsified / Failed"
          value={`${failedCount} Runs`}
          subtitle="Deflated Sharpe or latency fail"
          badge={{ text: "REJECTED", variant: "amber" }}
        />
        <MetricCard
          label="Trial Density"
          value="STR-002: 8 Models"
          subtitle="Multiple testing penalty active"
          badge={{ text: "DEFLATION EVAL", variant: "purple" }}
        />
      </div>

      {/* FILTER & SEARCH */}
      <Card variant="terminal">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search experiment ID, SHA, model..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded bg-[#0b0e14] border border-slate-800 text-xs font-mono-code text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
            {["ALL", "STR-001", "STR-002", "STR-003", "STR-004"].map((sid) => (
              <button
                key={sid}
                onClick={() => setSelectedStrategy(sid)}
                className={`px-3 py-1 rounded text-xs font-mono-code transition ${
                  selectedStrategy === sid
                    ? "bg-cyan-950 text-cyan-300 border border-cyan-700"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                {sid}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* EXPERIMENTS TABLE */}
      <Card variant="terminal">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Experiment ID</th>
                <th className="py-2.5 px-3">Strategy</th>
                <th className="py-2.5 px-3">Git SHA</th>
                <th className="py-2.5 px-3">Entry Model</th>
                <th className="py-2.5 px-3">Factor Model</th>
                <th className="py-2.5 px-3">Periods</th>
                <th className="py-2.5 px-3">Gate Outcome</th>
                <th className="py-2.5 px-3">Falsification / Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filtered.map((exp) => (
                <tr key={exp.experiment_id} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-bold text-cyan-400">{exp.experiment_id}</td>
                  <td className="py-2.5 px-3 font-semibold text-slate-200">{exp.strategy_id} v{exp.strategy_version}</td>
                  <td className="py-2.5 px-3 text-slate-400">{exp.git_sha ? exp.git_sha.slice(0, 7) : "UNKNOWN"}</td>
                  <td className="py-2.5 px-3 text-slate-200">{exp.entry_model}</td>
                  <td className="py-2.5 px-3 text-slate-400">{exp.factor_model}</td>
                  <td className="py-2.5 px-3 text-[11px] text-slate-400">
                    <div>Res: {exp.research_period}</div>
                    <div>Val: {exp.validation_period}</div>
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge
                      variant={
                        exp.gate_result === "PASS"
                          ? "emerald"
                          : exp.gate_result === "PENDING"
                          ? "amber"
                          : "rose"
                      }
                      size="xs"
                    >
                      {exp.gate_result}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate" title={exp.falsification_evidence || ""}>
                    {exp.falsification_evidence || exp.reasons?.join("; ") || "Nominal parameters"}
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
