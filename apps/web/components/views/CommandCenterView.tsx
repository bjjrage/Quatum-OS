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
  const gate24hRawState = status?.gate_24h?.status || recorder?.gate_24h_status;
  const gate24hElapsed = status?.gate_24h?.elapsed_seconds !== undefined
    ? status.gate_24h.elapsed_seconds
    : recorder?.elapsed_seconds;
  const hasGate24hRun = gate24hElapsed !== undefined && gate24hRawState !== undefined && gate24hRawState !== "UNKNOWN";
  const gate24hPassed = status?.gate_24h?.passed ?? (gate24hRawState === "PASS");
  const gate24hProgress = hasGate24hRun && gate24hElapsed !== undefined ? Math.min(100, (gate24hElapsed / 86400) * 100) : null;
  const gate24hStatus = !hasGate24hRun ? "UNKNOWN" : gate24hPassed ? "PASS" : gate24hRawState === "FAIL" ? "FAIL" : "PENDING";

  const gate72hRawState = status?.gate_72h?.status || recorder?.gate_72h_status;
  const gate72hElapsed = status?.gate_72h?.elapsed_seconds !== undefined
    ? status.gate_72h.elapsed_seconds
    : recorder?.elapsed_seconds;
  const hasGate72hRun = gate72hElapsed !== undefined && gate72hRawState !== undefined && gate72hRawState !== "UNKNOWN";
  const gate72hPassed = status?.gate_72h?.passed ?? (gate72hRawState === "PASS");
  const gate72hProgress = hasGate72hRun && gate72hElapsed !== undefined ? Math.min(100, (gate72hElapsed / 259200) * 100) : null;
  const gate72hStatus = !hasGate72hRun ? "UNKNOWN" : gate72hPassed ? "PASS" : gate72hRawState === "FAIL" ? "FAIL" : "PENDING";

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
              AUTHORIZED LIVE CAPITAL: $0.00 | LIVE ROUTING: CURRENTLY DISABLED
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
          value={recorder?.status || status?.recorder_status || "UNKNOWN"}
          subtitle={`Continuity: ${recorder?.continuity_state || status?.recorder_continuity || "UNKNOWN"}`}
          badge={{
            text: (recorder?.status || status?.recorder_status) === "RUNNING"
              ? "RUNNING"
              : (recorder?.status || status?.recorder_status) === "DEGRADED"
              ? "DEGRADED"
              : (recorder?.status || status?.recorder_status) === "STOPPED"
              ? "STOPPED"
              : "UNKNOWN",
            variant: (recorder?.status || status?.recorder_status) === "RUNNING"
              ? "emerald"
              : (recorder?.status || status?.recorder_status) === "DEGRADED"
              ? "amber"
              : (recorder?.status || status?.recorder_status) === "STOPPED"
              ? "rose"
              : "slate",
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
          value={status?.strategies_total !== undefined ? `${status.strategies_total} Strategies` : "UNKNOWN"}
          subtitle={status?.strategies_by_stage ? `Paper: ${status.strategies_by_stage.PAPER_ELIGIBLE ?? 0} | Research: ${status.strategies_by_stage.RESEARCH ?? 0}` : "Catalog uninitialized"}
          badge={{ text: status?.strategies_total !== undefined ? "CATALOG ACTIVE" : "UNINITIALIZED", variant: status?.strategies_total !== undefined ? "blue" : "slate" }}
          icon={<Layers className="w-4 h-4" />}
          onClick={() => onNavigate("strategy-registry")}
        />

        {(() => {
          const hasCiResults =
            status?.tests_passing !== undefined &&
            status.tests_passing !== null &&
            status?.tests_failing !== undefined &&
            status.tests_failing !== null;
          return (
            <MetricCard
              label="CI & Pytest Status"
              value={hasCiResults ? `${status.tests_passing} Passed / ${status.tests_failing} Failed` : "CI Status UNKNOWN"}
              subtitle="Coverage: Unit + Integration + API"
              badge={{
                text: hasCiResults ? (status.tests_failing === 0 ? "PASS" : "FAILURES") : "UNKNOWN",
                variant: hasCiResults ? (status.tests_failing === 0 ? "emerald" : "rose") : "slate",
              }}
              icon={<CheckCircle2 className="w-4 h-4" />}
              onClick={() => onNavigate("tests-ci")}
            />
          );
        })()}
      </div>

      {/* ACCEPTANCE GATES SECTION */}
      <Card
        title="24H & 72H Ingestion Acceptance Gates"
        subtitle="Mandatory continuity run requirement before any model promotion or live validation"
        variant="terminal"
        action={
          <Badge
            variant={
              gate24hStatus === "PASS" && gate72hStatus === "PASS"
                ? "emerald"
                : gate24hStatus === "UNKNOWN" || gate72hStatus === "UNKNOWN"
                ? "slate"
                : "amber"
            }
            size="sm"
          >
            {gate24hStatus === "PASS" && gate72hStatus === "PASS"
              ? "ACCEPTED"
              : gate24hStatus === "UNKNOWN" || gate72hStatus === "UNKNOWN"
              ? "GATES UNKNOWN"
              : "GATES PENDING"}
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
              <Badge
                variant={
                  gate24hStatus === "PASS"
                    ? "emerald"
                    : gate24hStatus === "FAIL"
                    ? "rose"
                    : gate24hStatus === "PENDING"
                    ? "amber"
                    : "slate"
                }
                size="xs"
              >
                {gate24hStatus === "PASS"
                  ? "PASS"
                  : gate24hStatus === "PENDING"
                  ? `PENDING (${gate24hElapsed !== undefined ? (gate24hElapsed / 3600).toFixed(1) : "0"}/24h)`
                  : gate24hStatus}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-[11px] font-mono-code text-slate-400">
                <span>
                  Elapsed:{" "}
                  {gate24hElapsed !== undefined
                    ? `${Math.floor(gate24hElapsed / 3600)}h ${Math.floor((gate24hElapsed % 3600) / 60)}m`
                    : "UNKNOWN"}
                </span>
                <span>Requirement: 24h 00m (86,400s)</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${gate24hProgress ?? 0}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 font-mono-code">
                {!hasGate24hRun
                  ? "Reason: No verified gate run telemetry recorded."
                  : gate24hStatus === "PASS"
                  ? "Reason: Continuous run requirement satisfied."
                  : `Reason: Duration elapsed (${gate24hElapsed?.toFixed(0)}s) < required threshold (86,400s). Gate cannot pass until full continuous run completes.`}
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
              <Badge
                variant={
                  gate72hStatus === "PASS"
                    ? "emerald"
                    : gate72hStatus === "FAIL"
                    ? "rose"
                    : gate72hStatus === "PENDING"
                    ? "amber"
                    : "slate"
                }
                size="xs"
              >
                {gate72hStatus === "PASS"
                  ? "PASS"
                  : gate72hStatus === "PENDING"
                  ? `PENDING (${gate72hElapsed !== undefined ? (gate72hElapsed / 3600).toFixed(1) : "0"}/72h)`
                  : gate72hStatus}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-[11px] font-mono-code text-slate-400">
                <span>
                  Elapsed:{" "}
                  {gate72hElapsed !== undefined
                    ? `${Math.floor(gate72hElapsed / 3600)}h ${Math.floor((gate72hElapsed % 3600) / 60)}m`
                    : "UNKNOWN"}
                </span>
                <span>Requirement: 72h 00m (259,200s)</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${gate72hProgress ?? 0}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 font-mono-code">
                {!hasGate72hRun
                  ? "Reason: No verified gate run telemetry recorded."
                  : gate72hStatus === "PASS"
                  ? "Reason: Continuous run requirement satisfied."
                  : `Reason: Duration elapsed (${gate72hElapsed?.toFixed(0)}s) < required threshold (259,200s).`}
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
            {(() => {
              const binanceVenue = recorder?.venues?.binance_perp;
              const deribitVenue = recorder?.venues?.deribit;
              const polymarketVenue = recorder?.venues?.polymarket;

              const venuesList = [
                {
                  venue: "Binance Futures (BTC/USDT, ETH/USDT)",
                  connected: binanceVenue?.connected ?? false,
                  status: !binanceVenue
                    ? "UNKNOWN"
                    : binanceVenue.connected
                    ? "READY / RECORDING"
                    : "STANDBY",
                  rate: binanceVenue?.event_rate !== undefined ? `${binanceVenue.event_rate.toFixed(1)} ev/s` : "UNKNOWN",
                  clockSkew: binanceVenue?.clock_skew_ms !== undefined ? `${binanceVenue.clock_skew_ms.toFixed(1)}ms` : "UNKNOWN",
                  format: "Parquet",
                  validation: !binanceVenue ? "UNVERIFIED" : binanceVenue.connected ? "MANIFEST OK" : "UNVERIFIED",
                  badgeVariant: !binanceVenue ? ("slate" as const) : binanceVenue.connected ? ("emerald" as const) : ("amber" as const),
                },
                {
                  venue: "Deribit (BTC/ETH DVol & Options)",
                  connected: deribitVenue?.connected ?? false,
                  status: !deribitVenue
                    ? "UNKNOWN"
                    : deribitVenue.connected
                    ? "READY / RECORDING"
                    : "STANDBY",
                  rate: deribitVenue?.event_rate !== undefined ? `${deribitVenue.event_rate.toFixed(1)} ev/s` : "UNKNOWN",
                  clockSkew: deribitVenue?.clock_skew_ms !== undefined ? `${deribitVenue.clock_skew_ms.toFixed(1)}ms` : "UNKNOWN",
                  format: "Parquet",
                  validation: !deribitVenue ? "UNVERIFIED" : deribitVenue.connected ? "MANIFEST OK" : "UNVERIFIED",
                  badgeVariant: !deribitVenue ? ("slate" as const) : deribitVenue.connected ? ("emerald" as const) : ("amber" as const),
                },
                {
                  venue: "Polymarket (Crypto Clustered Events)",
                  connected: polymarketVenue?.connected ?? false,
                  status: !polymarketVenue
                    ? "UNKNOWN"
                    : polymarketVenue.connected
                    ? "READY / POLLING"
                    : "STANDBY",
                  rate: polymarketVenue?.event_rate !== undefined ? `${polymarketVenue.event_rate.toFixed(1)} ev/s` : "UNKNOWN",
                  clockSkew: polymarketVenue?.clock_skew_ms !== undefined ? `${polymarketVenue.clock_skew_ms.toFixed(1)}ms` : "UNKNOWN",
                  format: "Parquet",
                  validation: !polymarketVenue ? "UNVERIFIED" : polymarketVenue.connected ? "MANIFEST OK" : "UNVERIFIED",
                  badgeVariant: !polymarketVenue ? ("slate" as const) : polymarketVenue.connected ? ("emerald" as const) : ("amber" as const),
                },
                {
                  venue: "Bybit (Perpetuals & Liquidity)",
                  connected: false,
                  status: "NO BASELINE / EVALUATION PENDING",
                  rate: "NO LIVE DATA",
                  clockSkew: "—",
                  format: "Parquet",
                  validation: "EVALUATION PENDING",
                  badgeVariant: "slate" as const,
                },
              ];

              return (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {venuesList.map((v) => (
                    <div
                      key={v.venue}
                      className="rounded border border-[#1d2331] bg-[#0c0e14] p-3 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-200 font-mono-code truncate">
                          {v.venue}
                        </span>
                        <Badge variant={v.badgeVariant} size="xs">
                          {v.status}
                        </Badge>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono-code text-slate-400">
                        <div>Rate: <span className="text-slate-300">{v.rate}</span></div>
                        <div>Skew: <span className="text-slate-300">{v.clockSkew}</span></div>
                        <div>Format: <span className="text-slate-300">{v.format}</span></div>
                        <div>Validation: <span className={v.connected ? "text-emerald-400" : "text-slate-400"}>{v.validation}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })()}
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
            subtitle="Live risk and operational alerts"
            action={
              <Badge variant="slate" size="xs">
                {!status ? "ALERTS: UNKNOWN" : `${status.system_alerts?.length ?? 0} ALERTS`}
              </Badge>
            }
          >
            <div className="space-y-3 pt-1">
              {!status ? (
                <div className="text-xs font-mono-code text-slate-500 py-3 text-center">
                  Backend alerts telemetry not available.
                </div>
              ) : !status.system_alerts || status.system_alerts.length === 0 ? (
                <div className="text-xs font-mono-code text-slate-500 py-3 text-center">
                  No active operational alerts reported by backend.
                </div>
              ) : (
                status.system_alerts.map((alert, idx) => (
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
                ))
              )}
            </div>
          </Card>

          {/* Documentary System Invariants Card */}
          <div className="rounded-lg border border-[#1b212f] bg-[#0c0e14] p-4 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono-code block">
              Architectural Invariants
            </span>
            <div className="space-y-2 text-xs font-mono-code">
              <div className="rounded border border-rose-900/40 bg-rose-950/20 p-2 text-rose-300">
                <div className="font-semibold flex items-center justify-between text-[11px]">
                  <span>[INVARIANT: LIVE_CAPITAL_ZERO]</span>
                  <Badge variant="rose" size="xs">ENFORCED</Badge>
                </div>
                <div className="text-[10px] opacity-90 mt-0.5">Live capital locked at $0.00. No order routing authorized.</div>
              </div>
              <div className="rounded border border-amber-900/40 bg-amber-950/20 p-2 text-amber-300">
                <div className="font-semibold flex items-center justify-between text-[11px]">
                  <span>[INVARIANT: STR002_EDGE_UNVALIDATED]</span>
                  <Badge variant="amber" size="xs">PENDING</Badge>
                </div>
                <div className="text-[10px] opacity-90 mt-0.5">STR-002 economic edge unvalidated until out-of-sample criteria pass.</div>
              </div>
            </div>
          </div>

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
                <span className="text-cyan-400 font-semibold">{status?.git_sha_short || "UNKNOWN"}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Active Branch:</span>
                <span className="text-slate-200">{status?.branch || "UNKNOWN"}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1">
                <span>Paper Broker Mode:</span>
                <span className={status?.environment === "LOCAL_PAPER_ONLY" ? "text-emerald-400 font-semibold" : "text-slate-400 font-semibold"}>
                  {status?.environment === "LOCAL_PAPER_ONLY"
                    ? "INTERNAL SIMULATED (LOCAL_PAPER_ONLY)"
                    : status?.environment
                    ? `SIMULATED (${status.environment})`
                    : "UNKNOWN"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Reconciliation Status:</span>
                <span className={status?.recorder_continuity === "CLEAN" ? "text-emerald-400" : "text-amber-400"}>
                  {status?.recorder_continuity ? `CONTINUITY: ${status.recorder_continuity}` : "UNVERIFIED"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
