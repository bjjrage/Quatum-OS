import React from "react";
import { Settings, ShieldCheck, Lock, HardDrive, Terminal, GitCommit } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

export function ConfigurationView() {
  const configs = [
    { key: "ENVIRONMENT", value: "OPERATIONAL_STAGING", status: "VERIFIED" },
    { key: "AUTHORIZED_LIVE_CAPITAL_USD", value: "0.00 (HARD INVARIANT)", status: "LOCKED" },
    { key: "LIVE_ORDER_ROUTING", value: "DISABLED (No API Keys Loaded)", status: "LOCKED" },
    { key: "DATA_RAW_DIR", value: "data/raw", status: "ONLINE" },
    { key: "RUNTIME_MANIFEST_PATH", value: "data/runtime/current_run.json", status: "ONLINE" },
    { key: "PYTHON_RUNTIME", value: "Python 3.12 (uv package manager)", status: "VERIFIED" },
    { key: "SEALED_HOLDOUT_DIR", value: "data/holdout (Encrypted/Sealed)", status: "SEALED" },
    { key: "CLOCK_SYNC_NTP_THRESHOLD_MS", value: "50.0 ms", status: "ACTIVE" },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-400" />
          Runtime Configuration & Invariant Parameters
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          System environment settings, directory partitions, and immutable security parameters.
        </p>
      </div>

      {/* METRIC STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Live Risk Lock"
          value="$0.00 USD"
          subtitle="Immutable parameter"
          badge={{ text: "LOCKED", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
        />
        <MetricCard
          label="Storage Architecture"
          value="Snappy Parquet"
          subtitle="Lakehouse partition tree"
          badge={{ text: "OPTIMIZED", variant: "cyan" }}
          icon={<HardDrive className="w-4 h-4" />}
        />
        <MetricCard
          label="Holdout Partition"
          value="SEALED"
          subtitle="Zero leakage isolation"
          badge={{ text: "SEALED", variant: "emerald" }}
        />
        <MetricCard
          label="Git Provenance"
          value="1d883a1 (main)"
          subtitle="Fully synchronized"
          badge={{ text: "CLEAN", variant: "blue" }}
          icon={<GitCommit className="w-4 h-4" />}
        />
      </div>

      {/* CONFIG TABLE */}
      <Card
        title="Active Environmental Configuration"
        subtitle="Current parameter values loaded in memory by Quant OS core process"
        variant="terminal"
      >
        <div className="overflow-x-auto pt-1">
          <table className="w-full text-xs font-mono-code text-left text-slate-300">
            <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Configuration Parameter</th>
                <th className="py-2.5 px-3">Loaded Value</th>
                <th className="py-2.5 px-3 text-right">Invariant State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {configs.map((c, i) => (
                <tr key={i} className="hover:bg-[#121622]/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-cyan-400">{c.key}</td>
                  <td className="py-2.5 px-3 text-slate-200">{c.value}</td>
                  <td className="py-2.5 px-3 text-right">
                    <Badge
                      variant={
                        c.status === "LOCKED"
                          ? "rose"
                          : c.status === "SEALED" || c.status === "ONLINE" || c.status === "VERIFIED"
                          ? "emerald"
                          : "slate"
                      }
                      size="xs"
                    >
                      {c.status}
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
