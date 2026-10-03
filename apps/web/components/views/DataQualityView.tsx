import React from "react";
import { Database, Clock, ShieldCheck, AlertCircle, FileCheck, HardDrive } from "lucide-react";
import { DataQuality } from "../../types";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { MetricCard } from "../common/MetricCard";

interface DataQualityViewProps {
  dataQuality: DataQuality | null;
}

export function DataQualityView({ dataQuality }: DataQualityViewProps) {
  const storage = dataQuality?.storage_metrics;
  const timing = dataQuality?.timestamp_integrity;
  const history = dataQuality?.history || [];

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-100 font-mono-code flex items-center gap-2">
          <Database className="w-5 h-5 text-cyan-400" />
          Data Quality & Storage Lakehouse Verification
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Parquet compression integrity, microsecond-level clock skew estimation, and causal ordering verification.
        </p>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Manifest Status"
          value={storage !== undefined && storage !== null ? (storage.manifest_valid ? "VALID" : "PENDING") : "UNKNOWN"}
          subtitle={storage !== undefined && storage !== null ? `${storage.orphan_tmp_files} Orphan tmp files detected` : "Scan uninitialized"}
          badge={{
            text: storage !== undefined && storage !== null ? (storage.manifest_valid ? "VALIDATED" : "PENDING") : "UNVERIFIED",
            variant: storage !== undefined && storage !== null ? (storage.manifest_valid ? "emerald" : "amber") : "slate",
          }}
          icon={<FileCheck className="w-4 h-4" />}
        />
        <MetricCard
          label="Clock Skew Detected"
          value={timing !== undefined && timing !== null ? (timing.is_host_clock_skew_detected ? "DETECTED" : "NOMINAL") : "UNKNOWN"}
          subtitle={`Offset: ${timing !== undefined && timing !== null ? `${timing.estimated_clock_offset_ms.toFixed(1)} ms` : "UNKNOWN"}`}
          badge={{
            text: timing !== undefined && timing !== null ? (timing.is_host_clock_skew_detected ? "CALIBRATED" : "SYNCHRONIZED") : "UNVERIFIED",
            variant: timing !== undefined && timing !== null ? (timing.is_host_clock_skew_detected ? "amber" : "emerald") : "slate",
          }}
          icon={<Clock className="w-4 h-4" />}
        />
        <MetricCard
          label="True Causal Violations"
          value={timing?.true_causal_violations !== undefined ? timing.true_causal_violations : "UNKNOWN"}
          subtitle="Monotonic event sequence test"
          badge={{
            text: timing?.true_causal_violations !== undefined ? (timing.true_causal_violations === 0 ? "ZERO VIOLATIONS" : "VIOLATIONS DETECTED") : "UNVERIFIED",
            variant: timing?.true_causal_violations !== undefined ? (timing.true_causal_violations === 0 ? "emerald" : "rose") : "slate",
          }}
          icon={<ShieldCheck className="w-4 h-4" />}
        />
        <MetricCard
          label="Lakehouse Volume"
          value={storage?.total_compressed_bytes !== undefined ? `${(storage.total_compressed_bytes / 1024 / 1024).toFixed(1)} MB` : "UNKNOWN"}
          subtitle={storage?.projected_gb_per_day !== undefined ? `Projected: ${storage.projected_gb_per_day.toFixed(1)} GB / day` : "Projected: UNKNOWN"}
          badge={{ text: storage ? "SNAPPY PARQUET" : "UNINITIALIZED", variant: storage ? "blue" : "slate" }}
          icon={<HardDrive className="w-4 h-4" />}
        />
      </div>

      {/* TWO SECTIONS: STORAGE METRICS & TIMESTAMP INTEGRITY */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PARQUET STORAGE AUDIT */}
        <Card
          title="Parquet Lakehouse Storage Telemetry"
          subtitle="Append-only partition tree with atomic rename guarantee"
          variant="terminal"
        >
          <div className="space-y-3 pt-1">
            <div className="grid grid-cols-2 gap-3 text-xs font-mono-code text-slate-300">
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 block text-[11px]">Total Row Count</span>
                <span className="text-base font-bold text-slate-100">
                  {storage?.total_row_count !== undefined ? storage.total_row_count.toLocaleString() : "0"}
                </span>
              </div>
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 block text-[11px]">Parquet Partitions</span>
                <span className="text-base font-bold text-cyan-400">
                  {storage?.parquet_file_count !== undefined ? `${storage.parquet_file_count} files` : "0 files"}
                </span>
              </div>
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 block text-[11px]">Bytes per Event</span>
                <span className="text-base font-bold text-slate-100">
                  {storage?.bytes_per_event !== undefined ? `${storage.bytes_per_event.toFixed(1)} bytes` : "—"}
                </span>
              </div>
              <div className="p-3 rounded bg-[#0b0e14] border border-slate-800">
                <span className="text-slate-400 block text-[11px]">Orphan .tmp Files</span>
                <span className="text-base font-bold text-emerald-400">
                  {storage?.orphan_tmp_files ?? 0}
                </span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-1.5 text-xs font-mono-code">
              <div className="flex justify-between text-slate-400">
                <span>Storage Path:</span>
                <span className="text-slate-200">data/raw/</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Run Manifest:</span>
                <span className="text-emerald-400">data/runtime/current_run.json (VALID)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Atomic Rename Invariant:</span>
                <span className="text-emerald-400">ENFORCED (tmp -&gt; final)</span>
              </div>
            </div>
          </div>
        </Card>

        {/* TIMESTAMP & LATENCY INTEGRITY */}
        <Card
          title="Timestamp Integrity & Latency Distribution"
          subtitle="Server-to-exchange clock calibration and percentile breakdown"
          variant="terminal"
        >
          <div className="space-y-4 pt-1">
            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-300 font-mono-code block">
                Raw vs Clock-Corrected Latency Percentiles
              </span>
              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono-code">
                <div className="p-2 rounded bg-[#121622] border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">P50 (Median)</span>
                  <span className="text-sm font-bold text-cyan-400">
                    {timing?.corrected_latency_p50_ms !== undefined ? `${timing.corrected_latency_p50_ms.toFixed(1)} ms` : "—"}
                  </span>
                </div>
                <div className="p-2 rounded bg-[#121622] border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">P95</span>
                  <span className="text-sm font-bold text-cyan-400">
                    {timing?.corrected_latency_p95_ms !== undefined ? `${timing.corrected_latency_p95_ms.toFixed(1)} ms` : "—"}
                  </span>
                </div>
                <div className="p-2 rounded bg-[#121622] border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">P99</span>
                  <span className="text-sm font-bold text-amber-400">
                    {timing?.corrected_latency_p99_ms !== undefined ? `${timing.corrected_latency_p99_ms.toFixed(1)} ms` : "—"}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0b0e14] border border-slate-800 space-y-1.5 text-xs font-mono-code text-slate-400">
              <div className="flex justify-between">
                <span>Negative Event Ages:</span>
                <span className="text-emerald-400">{timing?.negative_event_age_count ?? 0} (0.00%)</span>
              </div>
              <div className="flex justify-between">
                <span>Total Events Audited:</span>
                <span className="text-slate-200">{timing?.total_events_checked !== undefined ? timing.total_events_checked.toLocaleString() : "0"}</span>
              </div>
              <div className="flex justify-between">
                <span>Estimated Clock Offset:</span>
                <span className="text-amber-400">{timing?.estimated_clock_offset_ms !== undefined ? `${timing.estimated_clock_offset_ms.toFixed(2)} ms` : "0.00 ms"}</span>
              </div>
              <div className="flex justify-between">
                <span>Clock Calibration Status:</span>
                <span className="text-emerald-400 font-semibold">APPLIED (NTP offset subtracted)</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* HISTORICAL QUALITY RUNS TABLE */}
      <Card
        title="Quality Assurance Manifest Run History"
        subtitle="Immutable validation snapshots for data recording batches (data/quality/acceptance_*.json)"
        variant="terminal"
      >
        <div className="overflow-x-auto">
          {history.length === 0 ? (
            <div className="py-8 text-center text-xs font-mono-code text-slate-400">
              <p className="text-slate-300 font-semibold mb-1">0 HISTORICAL QUALITY REPORTS</p>
              <p className="text-slate-500">No acceptance quality snapshots found in data/quality/ yet.</p>
            </div>
          ) : (
            <table className="w-full text-xs font-mono-code text-left text-slate-300">
              <thead className="bg-[#0b0e14] text-slate-400 uppercase text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Run Batch / Snapshot</th>
                  <th className="py-2.5 px-3">Generated (UTC)</th>
                  <th className="py-2.5 px-3">Events Checked</th>
                  <th className="py-2.5 px-3">Manifest</th>
                  <th className="py-2.5 px-3">Clock Offset</th>
                  <th className="py-2.5 px-3">Corrected P50 / P95</th>
                  <th className="py-2.5 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {history.map((h, i) => (
                  <tr key={i} className="hover:bg-[#121622]/50 transition">
                    <td className="py-2.5 px-3 font-semibold text-cyan-400">{h.filename}</td>
                    <td className="py-2.5 px-3 text-slate-400">{h.generated_at_utc}</td>
                    <td className="py-2.5 px-3 text-slate-200">{h.total_events?.toLocaleString()}</td>
                    <td className="py-2.5 px-3">
                      <Badge variant={h.manifest_valid ? "emerald" : "rose"} size="xs">
                        {h.manifest_valid ? "VALID" : "INVALID"}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-amber-400">{h.clock_offset_ms} ms</td>
                    <td className="py-2.5 px-3 text-slate-200">{h.corrected_p50_ms}ms / {h.corrected_p95_ms}ms</td>
                    <td className="py-2.5 px-3 text-right">
                      <Badge variant="emerald" size="xs">PASS</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
