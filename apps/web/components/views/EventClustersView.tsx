import React from "react";
import { Calendar, AlertTriangle, ShieldCheck, Clock, Flame } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

export function EventClustersView() {
  const events = [
    {
      cluster_id: "EVT-FOMC-202611",
      name: "Federal Open Market Committee (FOMC) Rate Decision",
      category: "MACRO_MONETARY",
      scheduled_time: "2026-11-04 18:00 UTC",
      impact_level: "HIGH",
      blackout_window_mins: 30,
      leverage_multiplier: "0.25x",
      spread_buffer_bps: 12.0,
      affected_strategies: ["STR-001", "STR-002", "STR-003"],
      status: "SCHEDULED",
      action: "Mandatory order entry freeze 15m prior to release",
    },
    {
      cluster_id: "EVT-CPI-202610",
      name: "US Consumer Price Index (CPI) Release",
      category: "MACRO_INFLATION",
      scheduled_time: "2026-10-14 12:30 UTC",
      impact_level: "HIGH",
      blackout_window_mins: 20,
      leverage_multiplier: "0.50x",
      spread_buffer_bps: 8.0,
      affected_strategies: ["STR-001", "STR-002"],
      status: "SCHEDULED",
      action: "Volatility expansion protocol active",
    },
    {
      cluster_id: "EVT-DERIBIT-EXP-202610",
      name: "Deribit Monthly Options & Futures Expiry",
      category: "CRYPTO_DERIVATIVES",
      scheduled_time: "2026-10-30 08:00 UTC",
      impact_level: "MEDIUM",
      blackout_window_mins: 15,
      leverage_multiplier: "0.60x",
      spread_buffer_bps: 6.0,
      affected_strategies: ["STR-003", "STR-004"],
      status: "SCHEDULED",
      action: "Pin-risk monitoring and basis convergence filter",
    },
    {
      cluster_id: "EVT-BTC-HALV-HIST",
      name: "Bitcoin Network Halving Macro Anchor",
      category: "NETWORK_MONETARY",
      scheduled_time: "Cycle Anchor Baseline",
      impact_level: "STRUCTURAL",
      blackout_window_mins: 0,
      leverage_multiplier: "1.00x",
      spread_buffer_bps: 0.0,
      affected_strategies: ["STR-002", "STR-003"],
      status: "MONITORED",
      action: "Long-term liquidity floor parameter calibration",
    },
  ];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Calendar className="w-5 h-5 text-cyan-400" />
          Event Clusters, Volatility Regimes & Blackout Protocols
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          High-impact economic announcements and derivatives expiry clustering with autonomous sizing suppression.
        </p>
      </div>

      {/* METRIC ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Tracked Event Clusters"
          value={`${events.length} Clusters`}
          subtitle="Monetary, Inflation, Crypto"
          badge={{ text: "ACTIVE", variant: "cyan" }}
          icon={<Calendar className="w-4 h-4" />}
        />
        <MetricCard
          label="Active Blackout Window"
          value="INACTIVE (CLEAR)"
          subtitle="Next blackout: In 11 days (CPI)"
          badge={{ text: "NOMINAL TRADING", variant: "emerald" }}
          icon={<Clock className="w-4 h-4" />}
        />
        <MetricCard
          label="Max Volatility Multiplier"
          value="0.25x - 0.50x"
          subtitle="Dynamic leverage suppression"
          badge={{ text: "RISK GUARD", variant: "purple" }}
        />
        <MetricCard
          label="Blackout Compliance"
          value="100% ENFORCED"
          subtitle="Zero front-running or slippage spikes"
          badge={{ text: "AUDITED", variant: "emerald" }}
        />
      </div>

      {/* EVENT CLUSTERS LIST */}
      <Card
        title="High-Impact Event Schedule & Risk Regimes"
        subtitle="Automatic order-flow freezing and spread threshold widening"
        variant="terminal"
      >
        <div className="space-y-4 pt-1">
          {events.map((evt) => (
            <div
              key={evt.cluster_id}
              className="p-4 rounded-lg border border-[#1d2434] bg-[#0c0f16] space-y-3 hover:border-slate-700 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-100 font-mono-code">{evt.name}</span>
                    <Badge variant={evt.impact_level === "HIGH" ? "rose" : "amber"} size="xs">
                      {evt.impact_level} IMPACT
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400 mt-0.5 block font-mono-code">
                    Cluster ID: <span className="text-cyan-400">{evt.cluster_id}</span> | Scheduled: <span className="text-slate-200">{evt.scheduled_time}</span>
                  </span>
                </div>
                <Badge variant="cyan" size="xs">
                  {evt.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono-code text-slate-400">
                <div className="p-2 rounded bg-[#11141e] border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Blackout Window</span>
                  <span className="text-slate-200 font-semibold">{evt.blackout_window_mins} minutes</span>
                </div>
                <div className="p-2 rounded bg-[#11141e] border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Leverage Multiplier</span>
                  <span className="text-amber-400 font-semibold">{evt.leverage_multiplier}</span>
                </div>
                <div className="p-2 rounded bg-[#11141e] border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Spread Buffer</span>
                  <span className="text-slate-200 font-semibold">+{evt.spread_buffer_bps} bps</span>
                </div>
                <div className="p-2 rounded bg-[#11141e] border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Strategies Frozen</span>
                  <span className="text-cyan-400 font-semibold">{evt.affected_strategies.join(", ")}</span>
                </div>
              </div>

              <div className="text-[11px] font-mono-code text-slate-400 flex items-center gap-2">
                <span className="text-amber-400 font-semibold">Risk Protocol Directive:</span>
                <span>{evt.action}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
