import React from "react";
import { Lock, ShieldAlert, KeyRound, CheckCircle2, History, AlertOctagon } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface HoldoutsViewProps {
  holdoutsData?: {
    status: string;
    warning: string;
    total_openings: number;
    audits: any[];
  };
}

export function HoldoutsView({ holdoutsData }: HoldoutsViewProps) {
  const status = holdoutsData?.status || "UNKNOWN";
  const isKnown = Boolean(holdoutsData && holdoutsData.status !== "UNKNOWN");
  const isSealed = status === "SEALED";
  const openings = holdoutsData?.total_openings;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono-code flex items-center gap-2">
          <Lock className="w-5 h-5 text-rose-600 dark:text-rose-400" />
          Holdout Governance & Partition Manager
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 font-mono-code">
          Out-of-sample data partitions strictly reserved for final gate evaluation (isolation enforcement pending verification).
        </p>
      </div>

      {/* PROMINENT SEALED WARNING BANNER */}
      <div className="rounded-lg border border-rose-300 dark:border-rose-800/80 bg-rose-50 dark:bg-gradient-to-r dark:from-rose-950/60 dark:via-[#180a0e] dark:to-rose-950/30 p-5 shadow-xs dark:shadow-lg space-y-2">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-full bg-rose-100 dark:bg-rose-900/50 border border-rose-300 dark:border-rose-600 text-rose-800 dark:text-rose-300 animate-pulse-subtle">
            <AlertOctagon className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-rose-950 dark:text-rose-100 tracking-wider uppercase font-mono-code">
                CRITICAL PROTOCOL: HOLDOUT INTEGRITY & GOVERNANCE
              </span>
              <Badge variant={isSealed ? "rose" : isKnown ? "amber" : "slate"} size="xs">
                {status}
              </Badge>
            </div>
            <p className="text-xs text-rose-900/90 dark:text-rose-200/90 mt-1 leading-relaxed font-mono-code">
              Holdout partitions must remain strictly unobserved during model hyperparameter selection and exploratory data analysis.
              Opening a sealed holdout dataset irreversibly burns that partition and permanently invalidates further model iteration on that timeframe.
            </p>
          </div>
        </div>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Holdout Partition State"
          value={status}
          subtitle="Directory structure governance"
          badge={{
            text: !isKnown ? "UNVERIFIED" : isSealed ? "SEALED" : "COMPROMISED",
            variant: !isKnown ? "slate" : isSealed ? "emerald" : "rose",
          }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Total Historical Openings"
          value={openings !== undefined ? `${openings} Openings` : "UNKNOWN"}
          subtitle="Audit log record"
          badge={{
            text: openings === undefined ? "UNVERIFIED" : openings === 0 ? "UNTOUCHED" : "OPENED",
            variant: openings === undefined ? "slate" : openings === 0 ? "emerald" : "amber",
          }}
          icon={<History className="w-4 h-4" />}
        />
        <MetricCard
          label="Isolation Invariant"
          value="PENDING VERIFICATION"
          subtitle="Physical directory separation"
          badge={{ text: "PENDING", variant: "amber" }}
          icon={<ShieldAlert className="w-4 h-4" />}
        />
        <MetricCard
          label="Holdout Span"
          value="2026-07-01 to Present"
          subtitle="Reserved for live paper comparison"
          badge={{ text: "UNOBSERVED", variant: "blue" }}
        />
      </div>

      {/* AUDIT LOG TABLE */}
      <Card
        title="Holdout Opening Audit Log"
        subtitle="Audit ledger recording every interaction with out-of-sample datasets"
        variant="terminal"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono-code text-left text-slate-700 dark:text-slate-300">
            <thead className="bg-slate-100 dark:bg-[#0b0e14] text-slate-700 dark:text-slate-400 uppercase text-[11px] border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Audit Event ID</th>
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Operator / Principal</th>
                <th className="py-2.5 px-3">Target Partition</th>
                <th className="py-2.5 px-3">Action Type</th>
                <th className="py-2.5 px-3">Purpose & Signature</th>
                <th className="py-2.5 px-3 text-right">Vault Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
              {holdoutsData?.audits && holdoutsData.audits.length > 0 ? (
                holdoutsData.audits.map((a: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-[#121622]/50 transition">
                    <td className="py-2.5 px-3 font-semibold text-sky-600 dark:text-cyan-400">{a.id}</td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">{a.timestamp}</td>
                    <td className="py-2.5 px-3 text-slate-800 dark:text-slate-200">{a.operator}</td>
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">{a.partition}</td>
                    <td className="py-2.5 px-3">{a.action}</td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">{a.purpose}</td>
                    <td className="py-2.5 px-3 text-right">
                      <Badge variant="emerald" size="xs">LOGGED</Badge>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 dark:text-slate-400 font-mono-code">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 mx-auto mb-2 opacity-80" />
                    No holdout dataset openings recorded in local audit log.
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
