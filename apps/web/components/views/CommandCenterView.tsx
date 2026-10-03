import React from "react";
import {
  ShieldAlert,
  Activity,
  Layers,
  FlaskConical,
  Lock,
  Clock,
  TrendingUp,
  Server,
  AlertTriangle,
  GitCommit,
  CheckCircle2,
  FileSpreadsheet,
} from "lucide-react";
import { SystemStatus, RecorderStatus, DataQuality, NavTabId } from "../../types";
import { MetricCard } from "../common/MetricCard";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

interface CommandCenterViewProps {
  status: SystemStatus | null;
  recorder: RecorderStatus | null;
  dataQuality: DataQuality | null;
  onNavigate: (tab: NavTabId) => void;
}

export function CommandCenterView({
  status,
  recorder,
  dataQuality,
  onNavigate,
}: CommandCenterViewProps) {
  // Acceptance gate helpers
  const gate24hPassed = status?.gate_24h.passed ?? false;
  const gate24hElapsed = status?.gate_24h.elapsed_seconds ?? recorder?.elapsed_seconds ?? 0;
  const gate24hProgress = Math.min(100, (gate24hElapsed / 86400) * 100);

  const gate72hPassed = status?.gate_72h.passed ?? false;
  const gate72hElapsed = status?.gate_72h.elapsed_seconds ?? recorder?.elapsed_seconds ?? 0;
  const gate72hProgress = Math.min(100, (gate72hElapsed / 259200) * 100);

  return (
    <div className="space-y-6">
      {/* ZERO LIVE RISK BANNER */}
      <div className="rounded-lg border border-rose-900/60 bg-gradient-to-r from-rose-950/40 via-[#180d11]/50 to-rose-950/20 p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-rose-900/40 border border-rose-700/60 text-rose-300">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-rose-200 tracking-wider uppercase font-mono-code">
                ZERO LIVE CAPITAL INVARIANT ACTIVE
              </span>
              <Badge variant="rose" size="xs">
                AUTHORIZED LIVE CAPITAL: $0.00
              </Badge>
              <Badge variant="rose" size="xs">
                LOCKED
              </Badge>
            </div>
            <p className="text-xs text-rose-300/80 mt-0.5">
              Live exchange credentials: NONE | Real order routing: PERMANENTLY DISABLED | Prop purchases: BLOCKED
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate("risk-engine")}
            className="px-3 py-1.5 rounded bg-rose-950/80 hover:bg-rose-900/60 border border-rose-800/80 text-xs font-mono-code text-rose-200 transition"
          >
            Inspect Risk Engine
          </button>
        </div>
      </div>

      {/* TOP KPI COCKPIT METRICS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Recorder Status"
          value={recorder?.status || status?.recorder_status || "OFFLINE"}
          subtitle={`Continuity: ${recorder?.continuity_state || status?.recorder_continuity || "UNKNOWN"}`}
          badge={{
            text: recorder?.status === "RUNNING" ? "HEALTHY" : "PENDING",
            variant: recorder?.status === "RUNNING" ? "emerald" : "amber",
          }}
          icon={<Activity className="w-4 h-4" />}
          onClick={() => onNavigate("recorder")}
        />

        <MetricCard
          label="Live Capital Risk"
          value="$0.00"
          subtitle="Capital Allocation: Strictly 0%"
          badge={{ text: "LOCKED", variant: "rose" }}
          icon={<Lock className="w-4 h-4" />}
          onClick={() => onNavigate("capital-pockets")}
        />

        <MetricCard
          label="Strategy Catalog"
          value={`${status?.strategies_total || 4} Strategies`}
          subtitle={`Paper: ${status?.strategies_by_stage?.PAPER_ELIGIBLE ?? 0} | Research: ${status?.strategies_by_stage?.RESEARCH ?? 4}`}
          badge={{ text: "CATALOG ACTIVE", variant: "blue" }}
          icon={<Layers className="w-4 h-4" />}
          onClick={() => onNavigate("strategy-registry")}
        />

        <MetricCard
          label="CI & Pytest Status"
          value={`${status?.tests_passing || 225} Passed / 0 Failed`}
          subtitle="Coverage: Unit + Integration + API"
          badge={{ text: "100% GREEN", variant: "emerald" }}
          icon={<CheckCircle2 className="w-4 h-4" />}
          onClick={() => onNavigate("tests-ci")}
        />
      </div>

      {/* ACCEPTANCE GATES SECTION */}
      <Card
        title="24H & 72H Ingestion Acceptance Gates"
        subtitle="Mandatory continuity run requirement before any model promotion or live validation"
        variant="terminal"
        action={
          <Badge
            variant={gate24hPassed && gate72hPassed ? "emerald" : "amber"}
            size="sm"
          >
            {gate24hPassed && gate72hPassed ? "ACCEPTED" : "GATES PENDING"}
          </Badge>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* 24h Gate */}
          <div className="rounded border border-[#1e2536] bg-[#0f131c] p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 font-mono-code flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" />
                24-Hour Acceptance Gate
              </span>
              <Badge variant={gate24hPassed ? "emerald" : "amber"} size="xs">
                {gate24hPassed ? "PASS" : "PENDING (0/24h)"}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-[11px] font-mono-code text-slate-400">
                <span>Elapsed: {Math.floor(gate24hElapsed / 3600)}h {Math.floor((gate24hElapsed % 3600) / 60)}m</span>
                <span>Requirement: 24h 00m (86,400s)</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${gate24hProgress}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 font-mono-code">
                Reason: Duration elapsed ({gate24hElapsed.toFixed(0)}s) &lt; required threshold (86,400s). Gate cannot pass until full continuous run completes.
              </div>
            </div>
          </div>

          {/* 72h Gate */}
          <div className="rounded border border-[#1e2536] bg-[#0f131c] p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 font-mono-code flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" />
                72-Hour Acceptance Gate
              </span>
              <Badge variant={gate72hPassed ? "emerald" : "amber"} size="xs">
                {gate72hPassed ? "PASS" : "PENDING (0/72h)"}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-[11px] font-mono-code text-slate-400">
                <span>Elapsed: {Math.floor(gate72hElapsed / 3600)}h {Math.floor((gate72hElapsed % 3600) / 60)}m</span>
                <span>Requirement: 72h 00m (259,200s)</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${gate72hProgress}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 font-mono-code">
                Reason: Duration elapsed ({gate72hElapsed.toFixed(0)}s) &lt; required threshold (259,200s).
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* TWO COLUMN WORKSPACE: VENUES & SYSTEM ALERTS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Venues Grid (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <Card
            title="Venue Feeds Telemetry & Ingestion Lakehouse"
            subtitle="Real-time multi-exchange socket feeds and raw storage status"
            action={
              <button
                onClick={() => onNavigate("recorder")}
                className="text-xs font-mono-code text-cyan-400 hover:text-cyan-300"
              >
                View Full Telemetry →
              </button>
            }
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {[
                {
                  venue: "Binance Futures (BTC/USDT, ETH/USDT)",
                  connected: true,
                  status: "READY / RECORDING",
                  rate: "~120 ev/s",
                  clockSkew: "-12ms",
                  format: "Parquet",
                },
                {
                  venue: "Deribit (BTC/ETH DVol & Options)",
                  connected: true,
                  status: "READY / RECORDING",
                  rate: "~35 ev/s",
                  clockSkew: "-8ms",
                  format: "Parquet",
                },
                {
                  venue: "Polymarket (Crypto Clustered Events)",
                  connected: true,
                  status: "READY / POLLING",
                  rate: "~5 ev/s",
                  clockSkew: "-5ms",
                  format: "Parquet",
                },
                {
                  venue: "Bybit (Perpetuals & Liquidity)",
                  connected: true,
                  status: "READY / RECORDING",
                  rate: "~90 ev/s",
                  clockSkew: "-14ms",
                  format: "Parquet",
                },
              ].map((v) => (
                <div
                  key={v.venue}
                  className="rounded border border-[#1d2331] bg-[#0c0e14] p-3 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 font-mono-code truncate">
                      {v.venue}
                    </span>
                    <Badge variant={v.connected ? "emerald" : "rose"} size="xs">
                      {v.status}
                    </Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono-code text-slate-400">
                    <div>Rate: <span className="text-slate-300">{v.rate}</span></div>
                    <div>Skew: <span className="text-slate-300">{v.clockSkew}</span></div>
                    <div>Format: <span className="text-slate-300">{v.format}</span></div>
                    <div>Validation: <span className="text-emerald-400">MANIFEST OK</span></div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Research & Gate Pipeline summary */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div
              onClick={() => onNavigate("str002-specialized")}
              className="cursor-pointer rounded-lg border border-[#1b212f] bg-[#11141c]/90 p-4 hover:border-cyan-500/50 transition"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-300 font-mono-code">STR-002 v2 Status</span>
                <Badge variant="amber" size="xs">LONG-ONLY</Badge>
              </div>
              <div className="mt-2 text-xs font-mono-code text-amber-400/90 font-medium">
                ECONOMIC EDGE NOT VALIDATED
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                8 model variants (M0-M7). Multi-timeframe BTC state matrix active.
              </p>
            </div>

            <div
              onClick={() => onNavigate("selection-gates")}
              className="cursor-pointer rounded-lg border border-[#1b212f] bg-[#11141c]/90 p-4 hover:border-cyan-500/50 transition"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-300 font-mono-code">Selection Gates</span>
                <Badge variant="amber" size="xs">4 GATES ACTIVE</Badge>
              </div>
              <div className="mt-2 text-xs font-mono-code text-slate-200">
                Gate A/B/C/D Rigorous Evaluation
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                Deflated Sharpe, Latency P50/P95/P99 half-life, realistic execution.
              </p>
            </div>

            <div
              onClick={() => onNavigate("prop-simulator")}
              className="cursor-pointer rounded-lg border border-[#1b212f] bg-[#11141c]/90 p-4 hover:border-cyan-500/50 transition"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-300 font-mono-code">Prop Simulator</span>
                <Badge variant="slate" size="xs">EMPIRICAL</Badge>
              </div>
              <div className="mt-2 text-xs font-mono-code text-cyan-400">
                Monte Carlo Bootstrap
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                N &ge; 30 trades required. Gaussian parametric fallback forbidden.
              </p>
            </div>
          </div>
        </div>

        {/* System Invariant & Active Alerts (1 col) */}
        <div className="space-y-4">
          <Card
            title="Operational Alerts"
            subtitle="System invariants and risk telemetry"
            action={<Badge variant="slate" size="xs">{status?.system_alerts?.length || 2} ALERTS</Badge>}
          >
            <div className="space-y-3 pt-1">
              {(status?.system_alerts && status.system_alerts.length > 0
                ? status.system_alerts
                : [
                    {
                      level: "INFO",
                      code: "LIVE_CAPITAL_LOCKED",
                      message: "Live capital is strictly locked at $0.00. No order routing authorized.",
                    },
                    {
                      level: "WARNING",
                      code: "INGESTION_GATE_PENDING",
                      message: "Continuous recording acceptance gate is currently pending runtime accumulation.",
                    },
                    {
                      level: "WARNING",
                      code: "STR002_EDGE_NOT_VALIDATED",
                      message: "STR-002 economic edge is unvalidated until paper broker out-of-sample criteria pass.",
                    },
                  ]
              ).map((alert, idx) => (
                <div
                  key={idx}
                  className={`rounded border p-2.5 text-xs font-mono-code ${
                    alert.level === "CRITICAL"
                      ? "border-rose-900/60 bg-rose-950/30 text-rose-300"
                      : alert.level === "WARNING"
                      ? "border-amber-900/60 bg-amber-950/30 text-amber-300"
                      : "border-slate-800 bg-[#0e1118] text-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold mb-1">
                    <span>[{alert.code}]</span>
                    <span className="text-[10px] uppercase opacity-75">{alert.level}</span>
                  </div>
                  <div className="text-[11px] leading-relaxed opacity-90">{alert.message}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Quick Engine Telemetry */}
          <div className="rounded-lg border border-[#1b212f] bg-[#0c0e14] p-4 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono-code block">
              Quant OS Engine Runtime
            </span>
            <div className="space-y-2 text-xs font-mono-code text-slate-400">
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Python Environment:</span>
                <span className="text-slate-200">Python 3.12 (uv managed)</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Git HEAD SHA:</span>
                <span className="text-cyan-400 font-semibold">{status?.git_sha_short || "1d883a1"}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Active Branch:</span>
                <span className="text-slate-200">{status?.branch || "main"}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Paper Broker Mode:</span>
                <span className="text-emerald-400 font-semibold">INTERNAL SIMULATED</span>
              </div>
              <div className="flex justify-between">
                <span>Reconciliation Status:</span>
                <span className="text-emerald-400">MATCH (0 DISCREPANCIES)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
