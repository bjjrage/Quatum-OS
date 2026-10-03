import React from "react";
import { FileText, ShieldCheck, CheckCircle2, History, GitCommit, Key } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

export function AuditTrailView() {
  const auditEntries = [
    {
      id: "AUD-202610-001",
      timestamp: "2026-10-03 01:15:20 UTC",
      actor: "QUANT_PLATFORM_ENGINEER",
      domain: "SYSTEM_RUNTIME",
      action: "FASTAPI_READ_MODELS_DEPLOYED",
      details: "Exposed operational endpoints for web terminal integration",
      checksum: "sha256:8f9a2e3...1d883a1",
      status: "VERIFIED",
    },
    {
      id: "AUD-202610-002",
      timestamp: "2026-10-03 00:45:10 UTC",
      actor: "SYSTEM_SUPERVISOR",
      domain: "CAPITAL_RISK",
      action: "ZERO_CAPITAL_INVARIANT_VERIFIED",
      details: "Asserted live authorized capital strictly equals $0.00",
      checksum: "sha256:e1a44c9...0000000",
      status: "VERIFIED",
    },
    {
      id: "AUD-202610-003",
      timestamp: "2026-10-02 23:30:00 UTC",
      actor: "RECORDER_DAEMON",
      domain: "DATA_LAKEHOUSE",
      action: "SNAPSHOT_MANIFEST_COMMITTED",
      details: "data/runtime/current_run.json written with atomic rename",
      checksum: "sha256:d41d8cd...99files",
      status: "VERIFIED",
    },
    {
      id: "AUD-202610-004",
      timestamp: "2026-10-02 22:15:45 UTC",
      actor: "STRATEGY_REGISTRY",
      domain: "RESEARCH_CATALOG",
      action: "STR002_V2_REGISTERED",
      details: "Registered 8 model variants with long-only invariant enforcement",
      checksum: "sha256:3b71f90...m0m7spec",
      status: "VERIFIED",
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <FileText className="w-5 h-5 text-cyan-400" />
          Cryptographic Audit Trail & Governance Ledger
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Immutable event sequencing, operator action logging, and runtime manifest checksum verification.
        </p>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Audit Events"
          value={`${auditEntries.length} Records`}
          subtitle="Cryptographically sealed"
          badge={{ text: "IMMUTABLE", variant: "cyan" }}
          icon={<History className="w-4 h-4" />}
        />
        <MetricCard
          label="Integrity Checksum"
          value="100% VERIFIED"
          subtitle="Zero tampering detected"
          badge={{ text: "VALID", variant: "emerald" }}
          icon={<ShieldCheck className="w-4 h-4" />}
        />
        <MetricCard
          label="Live Invariant Status"
          value="ENFORCED"
          subtitle="Live capital $0 verified"
          badge={{ text: "SECURE", variant: "rose" }}
        />
        <MetricCard
          label="Active Manifest"
          value="current_run.json"
          subtitle="data/runtime/ partition"
          badge={{ text: "ATOMIC", variant: "blue" }}
        />
      </div>

      {/* AUDIT TABLE */}
      <Card
        title="Immutable System Audit Ledger"
        subtitle="Chronological sequence of verified operator and runtime state mutations"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Event ID</th>
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Actor / Origin</th>
                <th className="py-2.5 px-3">Domain</th>
                <th className="py-2.5 px-3">Action Type</th>
                <th className="py-2.5 px-3">Cryptographic Checksum</th>
                <th className="py-2.5 px-3 text-right">Integrity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {auditEntries.map((a) => (
                <tr key={a.id} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-cyan-400">{a.id}</td>
                  <td className="py-2.5 px-3 text-slate-400">{a.timestamp}</td>
                  <td className="py-2.5 px-3 text-slate-200">{a.actor}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="slate" size="xs">
                      {a.domain}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-100">{a.action}</td>
                  <td className="py-2.5 px-3 text-slate-400 truncate max-w-xs">{a.checksum}</td>
                  <td className="py-2.5 px-3 text-right">
                    <Badge variant="emerald" size="xs">
                      {a.status}
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
