"""CLI entrypoint for evaluating and generating Batch 0 Data Quality Acceptance Reports."""
import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Any

# Ensure root repository directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.quality.reporter import generate_quality_report


def print_ascii_summary(report: Dict[str, Any]) -> None:
    meta = report["report_metadata"]
    run = report["run_metadata"]
    health = report["runtime_health"]
    storage = report["storage_metrics"]
    ts = report["timestamp_integrity"]
    gates = report["gates"]
    cov = report["coverage_metrics"]

    print("=" * 80)
    print(" BATCH 0 MARKET DATA FOUNDATION — DATA QUALITY ACCEPTANCE REPORT")
    print("=" * 80)
    print(f"Overall State:       {meta['overall_state']}")
    print(f"Run ID:              {run['run_id']}")
    print(f"Git SHA:             {run['git_sha']}")
    print(f"Config Fingerprint:  {run['config_fingerprint']}")
    print(f"Started At (UTC):    {run['started_at_utc']}")
    print(f"Generated At (UTC):  {meta['generated_at_utc']}")
    print("-" * 80)
    print(" RUNTIME HEALTH")
    print("-" * 80)
    print(f"Process PID:         {health['pid']} (Alive: {health['is_process_alive']})")
    print(f"Elapsed Time:        {health['elapsed_formatted']} ({health['elapsed_seconds']:.1f}s)")
    print(f"Memory (RSS):        {health['rss_ram_mb']} MB")
    print(f"CPU Utilization:     {health['cpu_percent']} %")
    print("-" * 80)
    print(" STORAGE & MANIFEST METRICS")
    print("-" * 80)
    print(f"Parquet Part Files:  {storage['parquet_file_count']}")
    print(f"Total Rows:          {storage['total_row_count']}")
    print(f"Compressed Bytes:    {storage['total_compressed_bytes']:,} bytes ({storage['total_compressed_bytes'] / (1024*1024):.2f} MB)")
    print(f"Bytes / Event:       {storage['bytes_per_event']} B/evt")
    print(f"Projected Storage:   {storage['projected_gb_per_day']} GB/day")
    print(f"Orphan .tmp Files:   {storage['orphan_tmp_files']}")
    print(f"Manifest Verified:   {storage['manifest_valid']}")
    if storage["manifest_errors"]:
        for err in storage["manifest_errors"]:
            print(f"  [ERROR] {err}")
    print("-" * 80)
    print(" TIMESTAMP & LATENCY INTEGRITY")
    print("-" * 80)
    print(f"Events Checked:      {ts['total_events_checked']}")
    print(f"Raw Negative Ages:   {ts['negative_event_age_count']}")
    skew_str = f"DETECTED (~{abs(ts['estimated_clock_offset_ms']):.1f}ms local clock lag)" if ts.get('is_host_clock_skew_detected') else "SYNCHRONIZED (<100ms drift)"
    print(f"Host Clock Skew:     {skew_str}")
    print(f"Raw Latency (Local): P50={ts['latency_p50_ms']} ms | P95={ts['latency_p95_ms']} ms | P99={ts['latency_p99_ms']} ms")
    print(f"Corrected Transit:   P50={ts['corrected_latency_p50_ms']} ms | P95={ts['corrected_latency_p95_ms']} ms | P99={ts['corrected_latency_p99_ms']} ms")
    print(f"True Causal Anomalies: {ts.get('true_causal_violations', 0)} (Physically impossible violations)")
    print("-" * 80)
    print(" VENUE COVERAGE")
    print("-" * 80)
    print(f"Polymarket Active:   {cov['polymarket_active']}")
    print(f"Deribit Active:      {cov['deribit_active']}")
    print(f"Binance Perp Active: {cov['binance_active']} (OI Poller: {cov['binance_oi_active']})")
    print(f"Binance Coverage:    {cov['coverage_ratio']*100:.1f}% ({len(cov['binance_symbols_observed'])} observed, {len(cov['binance_symbols_missing'])} missing)")
    print("-" * 80)
    print(" EVIDENCE ACCEPTANCE GATES")
    print("-" * 80)
    g24 = gates["gate_24h"]
    g72 = gates["gate_72h"]
    print(f"24h Gate Status:     [{g24['status']}] (Elapsed: {g24['elapsed_seconds']:.1f}s / Required: {g24['required_seconds']:.1f}s)")
    for r in g24["reasons"]:
        print(f"  • {r}")
    print(f"72h Gate Status:     [{g72['status']}] (Elapsed: {g72['elapsed_seconds']:.1f}s / Required: {g72['required_seconds']:.1f}s)")
    for r in g72["reasons"]:
        print(f"  • {r}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch 0 Data Quality Acceptance Reporter")
    parser.add_argument("--data-dir", type=str, default=None, help="Base path to raw parquet data")
    parser.add_argument("--manifest", type=str, default=None, help="Path to current_run.json")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save quality reports")
    parser.add_argument("--json-only", action="store_true", help="Print raw JSON report to stdout only")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else None
    man_path = Path(args.manifest) if args.manifest else None
    out_dir = Path(args.output_dir) if args.output_dir else None

    report = generate_quality_report(
        base_data_path=data_dir,
        manifest_path=man_path,
        output_dir=out_dir,
    )

    if args.json_only:
        print(json.dumps(report, indent=2))
    else:
        print_ascii_summary(report)


if __name__ == "__main__":
    main()
