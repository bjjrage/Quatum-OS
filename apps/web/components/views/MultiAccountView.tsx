import React from "react";
import { Users, ShieldCheck, AlertTriangle, CheckCircle, Network, Layers } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

export function MultiAccountView() {
  const accounts = [
    {
      account_id: "ACCT-PROP-001",
      provider: "AlphaFunding",
      strategy: "STR-002 (M3 Variant)",
      balance_usd: 100000,
      isolation_state: "ISOLATED",
      jitter_delay_ms: 240,
      copy_trading_flag: "PASSED (NO DIRECT COPY)",
      pairwise_max_corr: 0.14,
      status: "COMPLIANT",
    },
    {
      account_id: "ACCT-PROP-002",
      provider: "AlphaFunding",
      strategy: "STR-002 (M4 Variant)",
      balance_usd: 100000,
      isolation_state: "ISOLATED",
      jitter_delay_ms: 480,
      copy_trading_flag: "PASSED (NO DIRECT COPY)",
      pairwise_max_corr: 0.18,
      status: "COMPLIANT",
    },
    {
      account_id: "ACCT-PROP-003",
      provider: "ApexEliteTrader",
      strategy: "STR-001 (StatArb)",
      balance_usd: 50000,
      isolation_state: "ISOLATED",
      jitter_delay_ms: 120,
      copy_trading_flag: "PASSED (NO DIRECT COPY)",
      pairwise_max_corr: 0.05,
      status: "COMPLIANT",
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Users className="w-5 h-5 text-cyan-400" />
          Multi-Account Compliance, Anti-Copy & Cross-Account Isolation
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Execution decorrelation, random order jittering, and hedging prevention across prop firm boundaries.
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Managed Prop Accounts"
          value={`${accounts.length} Accounts`}
          subtitle="AlphaFunding + Apex"
          badge={{ text: "ACTIVE", variant: "cyan" }}
          icon={<Layers className="w-4 h-4" />}
        />
        <MetricCard
          label="Cross-Account Hedging"
          value="ZERO DETECTED"
          subtitle="Opposing positions banned"
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
          label="Max Pairwise Correlation"
          value="0.18"
          subtitle="Threshold limit: 0.70"
          badge={{ text: "DECORRELATED", variant: "emerald" }}
        />
      </div>

      {/* MULTI ACCOUNT TABLE */}
      <Card
        title="Multi-Account Registry & Anti-Correlation Telemetry"
        subtitle="Verification of distinct parameters, model variant dispersion, and latency staggering"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Account ID</th>
                <th className="py-2.5 px-3">Provider Firm</th>
                <th className="py-2.5 px-3">Strategy Model</th>
                <th className="py-2.5 px-3">Balance USD</th>
                <th className="py-2.5 px-3">Isolation State</th>
                <th className="py-2.5 px-3">Jitter Buffer</th>
                <th className="py-2.5 px-3">Copy-Trading Test</th>
                <th className="py-2.5 px-3 text-right">Compliance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {accounts.map((a) => (
                <tr key={a.account_id} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-bold text-slate-100">{a.account_id}</td>
                  <td className="py-2.5 px-3 text-slate-400">{a.provider}</td>
                  <td className="py-2.5 px-3 text-cyan-400 font-semibold">{a.strategy}</td>
                  <td className="py-2.5 px-3 text-slate-200">${a.balance_usd.toLocaleString()}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="cyan" size="xs">
                      {a.isolation_state}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">+{a.jitter_delay_ms} ms</td>
                  <td className="py-2.5 px-3 text-emerald-400 font-semibold">{a.copy_trading_flag}</td>
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
