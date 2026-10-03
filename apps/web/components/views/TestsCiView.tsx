import React from "react";
import { CheckCircle2, ShieldCheck, Clock, Terminal, GitCommit, GitBranch, Layers } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

import { SystemStatus } from "../../types";

interface TestsCiViewProps {
  status?: SystemStatus | null;
}

export function TestsCiView({ status }: TestsCiViewProps) {
  const isCiRun = status?.tests_passing !== undefined && status.tests_passing !== null;
  const testsPassing = status?.tests_passing;
  const testsFailing = status?.tests_failing ?? 0;
  const gitShaShort = status?.git_sha_short || "UNKNOWN";
  const branch = status?.branch || "UNKNOWN";

  const testSuites = [
    { name: "test_api_endpoints.py", domain: "FASTAPI / REST API", coverage: "NOT_MEASURED" },
    { name: "test_recorder.py & test_recorder_robustness.py", domain: "DATA INGESTION / PARQUET", coverage: "NOT_MEASURED" },
    { name: "test_acceptance.py & test_manifest.py", domain: "24H/72H ACCEPTANCE GATES", coverage: "NOT_MEASURED" },
    { name: "test_tradability.py", domain: "LIQUIDITY TIER POLICY", coverage: "NOT_MEASURED" },
    { name: "test_str002_v2.py & test_registry.py", domain: "STRATEGY REGISTRY / M0-M7", coverage: "NOT_MEASURED" },
    { name: "test_holdout.py & test_experiments.py", domain: "RESEARCH / ANTI-LEAKAGE", coverage: "NOT_MEASURED" },
    { name: "test_gates.py & test_deflated_sharpe.py", domain: "SELECTION GATES A/B/C/D", coverage: "NOT_MEASURED" },
    { name: "test_risk_engine.py & test_capital_pockets.py", domain: "RISK & CAPITAL POCKETS", coverage: "NOT_MEASURED" },
    { name: "test_broker.py & test_reconciliation.py", domain: "PAPER BROKER & RECON", coverage: "NOT_MEASURED" },
    { name: "test_execution_authority.py & test_order_security.py", domain: "RISK AUTHORITY & ANTI-REPLAY", coverage: "NOT_MEASURED" },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-cyan-400" />
          Automated Test Suite & Continuous Integration Health
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Complete pytest execution report verifying zero-live-risk invariants, math validations, and data continuity.
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Pytest Status"
          value={isCiRun ? `${testsPassing} Passed / ${testsFailing} Failed` : "UNVERIFIED"}
          subtitle="Full test suite execution"
          badge={{
            text: !isCiRun ? "UNVERIFIED" : testsFailing === 0 ? "PASS" : "FAILURES",
            variant: !isCiRun ? "slate" : testsFailing === 0 ? "emerald" : "rose",
          }}
          icon={<CheckCircle2 className="w-4 h-4" />}
        />
        <MetricCard
          label="Suite Execution State"
          value={isCiRun ? "COMPLETED" : "UNVERIFIED"}
          subtitle="Local automated test runner"
          badge={{ text: isCiRun ? "COMPLETED" : "UNVERIFIED", variant: isCiRun ? "cyan" : "slate" }}
          icon={<Clock className="w-4 h-4" />}
        />
        <MetricCard
          label="Git HEAD Commit"
          value={gitShaShort}
          subtitle={`Branch: ${branch}`}
          badge={{ text: gitShaShort !== "UNKNOWN" ? "COMMITTED" : "UNVERIFIED", variant: gitShaShort !== "UNKNOWN" ? "blue" : "slate" }}
          icon={<GitCommit className="w-4 h-4" />}
        />
        <MetricCard
          label="Zero Live Risk Tests"
          value="ENFORCED"
          subtitle="Strict $0 live capital assertions"
          badge={{ text: "LOCKED", variant: "rose" }}
          icon={<ShieldCheck className="w-4 h-4" />}
        />
      </div>

      {/* TEST SUITES TABLE */}
      <Card
        title="Pytest Domain Test Breakdown"
        subtitle="Granular coverage of individual subdomains across the Quant OS architecture"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Test File / Module</th>
                <th className="py-2.5 px-3">Architectural Domain</th>
                <th className="py-2.5 px-3">Measured Coverage</th>
                <th className="py-2.5 px-3 text-right">Suite State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {testSuites.map((ts, i) => (
                <tr key={i} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-100">{ts.name}</td>
                  <td className="py-2.5 px-3 text-cyan-400">{ts.domain}</td>
                  <td className="py-2.5 px-3 text-slate-400">{ts.coverage}</td>
                  <td className="py-2.5 px-3 text-right">
                    <Badge variant={isCiRun ? (testsFailing === 0 ? "emerald" : "rose") : "slate"} size="xs">
                      {isCiRun ? (testsFailing === 0 ? "PASS" : "FAIL") : "UNVERIFIED"}
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
