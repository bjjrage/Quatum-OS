import React from "react";
import { Activity, Clock, Database, HardDrive, RefreshCw, Server, AlertCircle } from "lucide-react";
import { RecorderStatus, DataQuality } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface RecorderViewProps {
  recorder: RecorderStatus | null;
  dataQuality: DataQuality | null;
  onRefresh?: () => void;
}

export function RecorderView({ recorder, dataQuality, onRefresh }: RecorderViewProps) {
  const hasRun = recorder !== null && recorder !== undefined && recorder.elapsed_seconds !== undefined;
  const elapsed = recorder?.elapsed_seconds;
  const elapsedHours = elapsed !== undefined ? Math.floor(elapsed / 3600) : 0;
  const elapsedMins = elapsed !== undefined ? Math.floor((elapsed % 3600) / 60) : 0;
  const elapsedSecs = elapsed !== undefined ? Math.floor(elapsed % 60) : 0;

  const gate24hPassed = recorder?.gate_24h_status === "PASS";
  const gate72hPassed = recorder?.gate_72h_status === "PASS";
  const gate24hState = !hasRun ? "UNKNOWN" : gate24hPassed ? "PASS" : recorder?.gate_24h_status === "FAIL" ? "FAIL" : "PENDING";
  const gate72hState = !hasRun ? "UNKNOWN" : gate72hPassed ? "PASS" : recorder?.gate_72h_status === "FAIL" ? "FAIL" : "PENDING";

  const pct24h = elapsed !== undefined ? Math.min(100, (elapsed / 86400) * 100) : null;
  const pct72h = elapsed !== undefined ? Math.min(100, (elapsed / 259200) * 100) : null;

  // Real venue telemetry only
  const venues = recorder?.venues ?? {};

  return (
    <div className="space-y-6">
      {/* HEADER CONTROLS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Market Recorder & Raw Ingestion Telemetry
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time websocket feed capture, append-only Parquet storage, and strict acceptance timer validation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="cyan" size="sm">
            RUN ID: {recorder?.run_id ? recorder.run_id.slice(0, 8) : "STANDBY"}
          </Badge>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono-code text-slate-200 border border-slate-700 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Feeds
            </button>
          )}
        </div>
      </div>

      {/* TOP STATS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Recorder Status"
          value={recorder?.status || "STANDBY"}
          subtitle={`PID: ${recorder?.pid ?? "—"} | Alive: ${recorder?.is_process_alive ? "YES" : "NO"}`}
          badge={{
            text: recorder?.is_process_alive ? "PROCESS OK" : "STANDBY",
            variant: recorder?.is_process_alive ? "emerald" : "amber",
          }}
          icon={<Server className="w-4 h-4" />}
        />
        <MetricCard
          label="Continuity State"
          value={recorder?.continuity_state || "UNKNOWN"}
          subtitle="Zero unhandled process crashes"
          badge={{
            text: recorder?.continuity_state || "UNVERIFIED",
            variant: recorder?.continuity_state === "CLEAN" || recorder?.continuity_state === "UNBROKEN" ? "emerald" : "amber",
          }}
          icon={<Activity className="w-4 h-4" />}
        />
        <MetricCard
          label="Elapsed Run Time"
          value={elapsed !== undefined ? `${elapsedHours}h ${elapsedMins}m ${elapsedSecs}s` : "UNKNOWN"}
          subtitle="Continuous recording clock"
          badge={{ text: elapsed !== undefined ? "MONITORING" : "STANDBY", variant: elapsed !== undefined ? "blue" : "slate" }}
          icon={<Clock className="w-4 h-4" />}
        />
        <MetricCard
          label="Parquet Lakehouse"
          value={dataQuality?.storage_metrics?.parquet_file_count !== undefined ? `${dataQuality.storage_metrics.parquet_file_count} Files` : "UNKNOWN"}
          subtitle={dataQuality?.storage_metrics?.total_compressed_bytes !== undefined ? `Size: ${(((dataQuality.storage_metrics.total_compressed_bytes) / 1024 / 1024).toFixed(1))} MB` : "Size: UNKNOWN"}
          badge={{
            text: dataQuality?.storage_metrics?.manifest_valid !== undefined ? (dataQuality.storage_metrics.manifest_valid ? "MANIFEST VALID" : "INVALID") : "UNVERIFIED",
            variant: dataQuality?.storage_metrics?.manifest_valid ? "emerald" : "amber",
          }}
          icon={<HardDrive className="w-4 h-4" />}
        />
      </div>

      {/* 24H & 72H ACCEPTANCE GATES */}
      <Card
        title="Ingestion Acceptance Criteria (24-Hour & 72-Hour Gates)"
        subtitle="Operational standard: A candidate data recording must continuously run without gaps, crashes, or schema corruption before model promotion."
        variant="terminal"
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
          {/* 24-HOUR GATE */}
          <div className="p-4 rounded-lg border border-[#1e2536] bg-[#0c0f16] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 font-mono-code uppercase">
                Gate 1: 24-Hour Continuous Recording
              </span>
              <Badge
                variant={
                  gate24hState === "PASS"
                    ? "emerald"
                    : gate24hState === "FAIL"
                    ? "rose"
                    : gate24hState === "PENDING"
                    ? "amber"
                    : "slate"
                }
                size="xs"
              >
                {gate24hState === "PASS"
                  ? "PASS"
                  : gate24hState === "PENDING"
                  ? `PENDING (${elapsed !== undefined ? (elapsed / 3600).toFixed(1) : 0}/24h)`
                  : gate24hState}
              </Badge>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono-code text-slate-300">
                <span>Progress: {pct24h !== null ? `${pct24h.toFixed(1)}%` : "UNKNOWN"}</span>
                <span>Requirement: 86,400s</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct24h ?? 0}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] font-mono-code text-slate-400 bg-[#121622] p-2.5 rounded border border-slate-800">
              <span className="text-amber-400 font-semibold">Verification Reason:</span>{" "}
              {!hasRun
                ? "No verified gate run telemetry recorded."
                : gate24hPassed
                ? "Continuous run requirement satisfied."
                : `Elapsed time (${elapsed?.toFixed(0)}s) < required continuous threshold (86,400s). Gate status remains strictly PENDING until the full 24 hours of unbroken recording have completed.`}
            </div>
          </div>

          {/* 72-HOUR GATE */}
          <div className="p-4 rounded-lg border border-[#1e2536] bg-[#0c0f16] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 font-mono-code uppercase">
                Gate 2: 72-Hour Continuous Recording
              </span>
              <Badge
                variant={
                  gate72hState === "PASS"
                    ? "emerald"
                    : gate72hState === "FAIL"
                    ? "rose"
                    : gate72hState === "PENDING"
                    ? "amber"
                    : "slate"
                }
                size="xs"
              >
                {gate72hState === "PASS"
                  ? "PASS"
                  : gate72hState === "PENDING"
                  ? `PENDING (${elapsed !== undefined ? (elapsed / 3600).toFixed(1) : 0}/72h)`
                  : gate72hState}
              </Badge>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono-code text-slate-300">
                <span>Progress: {pct72h !== null ? `${pct72h.toFixed(1)}%` : "UNKNOWN"}</span>
                <span>Requirement: 259,200s</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                <div
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct72h ?? 0}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] font-mono-code text-slate-400 bg-[#121622] p-2.5 rounded border border-slate-800">
              <span className="text-cyan-400 font-semibold">Verification Reason:</span>{" "}
              {!hasRun
                ? "No verified gate run telemetry recorded."
                : gate72hPassed
                ? "Continuous run requirement satisfied."
                : `Elapsed time (${elapsed?.toFixed(0)}s) < required threshold (259,200s). Gate ensures full weekend cross-market continuity and liquidity regime transition survival.`}
            </div>
          </div>
        </div>
      </Card>

      {/* VENUES MATRIX */}
      <div>
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono-code mb-3">
          Exchange Venue Telemetry Matrix
        </h3>
        {Object.keys(venues).length === 0 ? (
          <div className="p-6 rounded-lg border border-[#1e2536] bg-[#0c0f16] text-center text-xs font-mono-code text-slate-500">
            No venue telemetry available from recorder process.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(venues).map(([key, v]) => (
              <Card key={key} variant="terminal" className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${v.connected ? "bg-emerald-400" : "bg-rose-500"} animate-pulse-subtle`} />
                    <span className="text-sm font-bold text-slate-100 font-mono-code">{v.venue}</span>
                  </div>
                  <Badge variant={key === "bybit" ? "amber" : (v.connected ? "emerald" : "rose")} size="xs">
                    {key === "bybit" ? "NO BASELINE" : (v.connected ? "CONNECTED" : "DISCONNECTED")}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs font-mono-code text-slate-400">
                  <div className="flex justify-between">
                    <span>Total Events:</span>
                    <span className="text-slate-200">{v.total_events !== undefined ? v.total_events.toLocaleString() : "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Event Rate:</span>
                    <span className="text-cyan-400 font-semibold">{v.event_rate !== undefined ? `${v.event_rate.toFixed(1)} ev/s` : "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Feed Lag:</span>
                    <span className="text-slate-200">{v.lag_ms !== undefined ? `${v.lag_ms} ms` : "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Clock Skew:</span>
                    <span className={v.clock_skew_detected ? "text-amber-400 font-medium" : "text-emerald-400"}>
                      {v.clock_skew_ms !== undefined && v.clock_skew_ms !== null ? `${v.clock_skew_ms.toFixed(1)} ms` : "UNKNOWN"} {v.clock_skew_detected ? "(offset)" : ""}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Parquet Files:</span>
                    <span className="text-slate-200">{v.files_written !== undefined ? `${v.files_written} parts` : "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Storage Size:</span>
                    <span className="text-slate-200">{v.storage_size_bytes !== undefined ? `${((v.storage_size_bytes) / 1024 / 1024).toFixed(1)} MB` : "UNKNOWN"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Manifest Health:</span>
                    <span className={v.manifest_health === "VALID" ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                      {v.manifest_health || "UNVERIFIED"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Dropped Events:</span>
                    <span className="text-emerald-400">{v.dropped_or_invalid_events !== undefined ? v.dropped_or_invalid_events : "UNKNOWN"}</span>
                  </div>
                  {v.notes && (
                    <div className="col-span-2 mt-1 text-[11px] font-mono-code text-amber-300/90 bg-amber-950/20 border border-amber-900/40 p-2 rounded">
                      {v.notes}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
