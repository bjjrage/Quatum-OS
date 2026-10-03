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
  const elapsed = recorder?.elapsed_seconds ?? 0;
  const elapsedHours = Math.floor(elapsed / 3600);
  const elapsedMins = Math.floor((elapsed % 3600) / 60);
  const elapsedSecs = Math.floor(elapsed % 60);

  const gate24hPassed = recorder?.gate_24h_status === "PASS";
  const gate72hPassed = recorder?.gate_72h_status === "PASS";

  const pct24h = Math.min(100, (elapsed / 86400) * 100);
  const pct72h = Math.min(100, (elapsed / 259200) * 100);

  // Real or nominal telemetry
  const venues = recorder?.venues ?? {
    binance_perp: {
      venue: "Binance Futures (BTC/ETH Perp)",
      connected: recorder?.is_process_alive ?? false,
      total_events: 0,
      event_rate: 0.0,
      lag_ms: 0,
      clock_skew_detected: false,
      clock_skew_ms: 0.0,
      files_written: 0,
      manifest_health: "PENDING",
      dropped_or_invalid_events: 0,
      storage_size_bytes: 0,
    },
    deribit: {
      venue: "Deribit (Options & DVol)",
      connected: recorder?.is_process_alive ?? false,
      total_events: 0,
      event_rate: 0.0,
      lag_ms: 0,
      clock_skew_detected: false,
      clock_skew_ms: 0.0,
      files_written: 0,
      manifest_health: "PENDING",
      dropped_or_invalid_events: 0,
      storage_size_bytes: 0,
    },
    polymarket: {
      venue: "Polymarket (Event Gamma)",
      connected: recorder?.is_process_alive ?? false,
      total_events: 0,
      event_rate: 0.0,
      lag_ms: 0,
      clock_skew_detected: false,
      clock_skew_ms: 0.0,
      files_written: 0,
      manifest_health: "PENDING",
      dropped_or_invalid_events: 0,
      storage_size_bytes: 0,
    },
    bybit: {
      venue: "Bybit (Perpetuals & Liquidity)",
      connected: false,
      total_events: 0,
      event_rate: 0.0,
      lag_ms: 0,
      clock_skew_detected: false,
      clock_skew_ms: 0.0,
      files_written: 0,
      manifest_health: "EVALUATION PENDING",
      dropped_or_invalid_events: 0,
      storage_size_bytes: 0,
      notes: "Batch 0: No baseline ingestion. Evaluation pending.",
    },
  };

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
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-xs font-mono-code text-slate-800 border border-slate-300 shadow-xs font-semibold dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 dark:border-slate-700 transition"
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
          value={recorder?.continuity_state || "UNBROKEN"}
          subtitle="Zero unhandled process crashes"
          badge={{ text: recorder?.continuity_state || "UNBROKEN", variant: "emerald" }}
          icon={<Activity className="w-4 h-4" />}
        />
        <MetricCard
          label="Elapsed Run Time"
          value={`${elapsedHours}h ${elapsedMins}m ${elapsedSecs}s`}
          subtitle="Continuous recording clock"
          badge={{ text: "MONITORING", variant: "blue" }}
          icon={<Clock className="w-4 h-4" />}
        />
        <MetricCard
          label="Parquet Lakehouse"
          value={`${dataQuality?.storage_metrics?.parquet_file_count ?? 0} Files`}
          subtitle={`Size: ${(((dataQuality?.storage_metrics?.total_compressed_bytes ?? 0) / 1024 / 1024).toFixed(1))} MB`}
          badge={{
            text: dataQuality?.storage_metrics?.manifest_valid ? "MANIFEST VALID" : "PENDING",
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
              <Badge variant={gate24hPassed ? "emerald" : "amber"} size="xs">
                {gate24hPassed ? "PASS" : "PENDING (0/24h)"}
              </Badge>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono-code text-slate-300">
                <span>Progress: {pct24h.toFixed(1)}%</span>
                <span>Requirement: 86,400s</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct24h}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] font-mono-code text-slate-400 bg-[#121622] p-2.5 rounded border border-slate-800">
              <span className="text-amber-400 font-semibold">Verification Reason:</span> Elapsed time ({elapsed.toFixed(0)}s) &lt; required continuous threshold (86,400s). In accordance with system policy, gate status remains strictly PENDING until the full 24 hours of unbroken recording have completed.
            </div>
          </div>

          {/* 72-HOUR GATE */}
          <div className="p-4 rounded-lg border border-[#1e2536] bg-[#0c0f16] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 font-mono-code uppercase">
                Gate 2: 72-Hour Continuous Recording
              </span>
              <Badge variant={gate72hPassed ? "emerald" : "amber"} size="xs">
                {gate72hPassed ? "PASS" : "PENDING (0/72h)"}
              </Badge>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono-code text-slate-300">
                <span>Progress: {pct72h.toFixed(1)}%</span>
                <span>Requirement: 259,200s</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                <div
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct72h}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] font-mono-code text-slate-400 bg-[#121622] p-2.5 rounded border border-slate-800">
              <span className="text-cyan-400 font-semibold">Verification Reason:</span> Elapsed time ({elapsed.toFixed(0)}s) &lt; required threshold (259,200s). Gate ensures full weekend cross-market continuity and liquidity regime transition survival.
            </div>
          </div>
        </div>
      </Card>

      {/* VENUE CARDS DETAIL */}
      <div>
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono-code mb-3">
          Exchange Venue Telemetry Matrix
        </h3>
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
                  <span className="text-slate-200">{v.total_events.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Event Rate:</span>
                  <span className="text-cyan-400 font-semibold">{v.event_rate} ev/s</span>
                </div>
                <div className="flex justify-between">
                  <span>Feed Lag:</span>
                  <span className="text-slate-200">{v.lag_ms ?? 0} ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Clock Skew:</span>
                  <span className={v.clock_skew_detected ? "text-amber-400 font-medium" : "text-emerald-400"}>
                    {v.clock_skew_ms?.toFixed(1) ?? "0.0"} ms {v.clock_skew_detected ? "(offset)" : ""}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Parquet Files:</span>
                  <span className="text-slate-200">{v.files_written} parts</span>
                </div>
                <div className="flex justify-between">
                  <span>Storage Size:</span>
                  <span className="text-slate-200">{((v.storage_size_bytes ?? 0) / 1024 / 1024).toFixed(1)} MB</span>
                </div>
                <div className="flex justify-between">
                  <span>Manifest Health:</span>
                  <span className={v.manifest_health === "VALID" ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                    {v.manifest_health}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Dropped Events:</span>
                  <span className="text-emerald-400">{v.dropped_or_invalid_events ?? 0}</span>
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
      </div>
    </div>
  );
}
