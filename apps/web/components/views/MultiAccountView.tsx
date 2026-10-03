import React, { useState, useEffect } from "react";
import { Users, ShieldCheck, AlertTriangle, CheckCircle, Network, Layers, Lock, ShieldAlert } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";
import { api } from "../../lib/api";

interface MultiAccountViewProps {
  complianceData?: any[];
}

export function MultiAccountView({ complianceData }: MultiAccountViewProps) {
  const [compliance, setCompliance] = useState<any[]>(complianceData || []);

  useEffect(() => {
    if (!complianceData || complianceData.length === 0) {
      api.getMultiAccountCompliance().then((res) => {
        if (res && res.length > 0) setCompliance(res);
      });
    }
  }, [complianceData]);

  const activeAccountsCount = 0; // Live invariant: $0 live capital, 0 active live accounts

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <Users className="w-5 h-5 text-cyan-400" />
            Multi-Account Compliance, Anti-Copy & Cross-Account Isolation
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Execution decorrelation, random order jittering, and hedging prevention across prop firm boundaries.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="rose" size="sm">
            LIVE ACCOUNTS: 0 ($0 RISK)
          </Badge>
          <Badge variant="cyan" size="sm">
            EVIDENCE GATE: ENFORCED
          </Badge>
        </div>
      </div>

      {/* CORE INVARIANT BANNER */}
      <div className="rounded-lg border border-rose-900/60 bg-rose-950/20 p-4 text-xs font-mono-code space-y-1">
        <div className="flex items-center gap-2 text-rose-300 font-bold uppercase">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          Live Capital Locked Invariant ($0 Live Risk)
        </div>
        <p className="text-slate-300 leading-relaxed">
          The system strictly forbids unauthorized purchase of prop evaluations or binding live API credentials.
          All multi-account rule policies are verified ahead of time through the <strong className="text-rose-200">MultiAccountEvidenceGate</strong> before any capital can be provisioned.
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Funded Accounts"
          value={`${activeAccountsCount} Accounts`}
          subtitle="Authorized live capital: $0.00"
          badge={{ text: "LOCKED ($0)", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Cross-Account Hedging"
          value="STRICTLY BANNED"
          subtitle="Opposing positions vetoed"
          badge={{ text: "COMPLIANT", variant: "emerald" }}
          icon={<ShieldCheck className="w-4 h-4" />}
        />
        <MetricCard
          label="Order Arrival Jitter"
          value="ENABLED"
          subtitle="Randomized +-500ms delay"
          badge={{ text: "ANTI-COPY", variant: "purple" }}
        />
        <MetricCard
          label="Registered Providers"
          value={`${compliance.length} Providers`}
          subtitle="Legal terms compliance tracked"
          badge={{ text: "AUDITED", variant: "cyan" }}
          icon={<Layers className="w-4 h-4" />}
        />
      </div>

      {/* PROVIDER TERMS COMPLIANCE TABLE */}
      <Card
        title="Prop Provider Anti-Copy & Multi-Account Terms Registry"
        subtitle="Formal contract addendums and bot policy verification (src/risk/capital_pockets.py)"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Provider Firm</th>
                <th className="py-2.5 px-3">Multiple Accounts</th>
                <th className="py-2.5 px-3">Same Bot Allowed</th>
                <th className="py-2.5 px-3">Copy-Trading Policy</th>
                <th className="py-2.5 px-3">Written Evidence</th>
                <th className="py-2.5 px-3">Second Account Gate</th>
                <th className="py-2.5 px-3 text-right">Contract Reference</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {compliance.map((c, i) => (
                <tr key={i} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-bold text-slate-100">{c.provider_name}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant={c.multiple_accounts_allowed ? "emerald" : "rose"} size="xs">
                      {c.multiple_accounts_allowed ? "ALLOWED" : "PROHIBITED"}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant={c.same_bot_allowed ? "emerald" : "rose"} size="xs">
                      {c.same_bot_allowed ? "ALLOWED" : "PROHIBITED"}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-300">
                    {c.same_bot_considered_copy_trading ? "FLAGGED AS COPY" : "PERMITTED"}
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant={c.written_evidence_status === "VERIFIED" ? "emerald" : "amber"} size="xs">
                      {c.written_evidence_status}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge variant={c.second_account_status === "PASS" ? "emerald" : "amber"} size="xs">
                      {c.second_account_status}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-400">{c.verified_contract_ref}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ACTIVE ACCOUNTS REGISTRY (EMPTY STATE) */}
      <Card
        title="Allocated Multi-Account Execution Instances"
        subtitle="Physical sub-accounts and independent order execution routing"
        variant="terminal"
      >
        <div className="py-10 text-center text-xs font-mono-code text-slate-400">
          <p className="text-slate-200 font-bold mb-1">0 ACTIVE LIVE ACCOUNTS</p>
          <p className="text-slate-500 max-w-md mx-auto">
            Live capital is strictly locked at $0.00. No real prop firm accounts have been purchased or connected. MultiAccountEvidenceGate is active and ready for evaluation.
          </p>
        </div>
      </Card>
    </div>
  );
}
