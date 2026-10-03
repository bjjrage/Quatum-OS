"""Quality report generation and acceptance gate orchestration."""
import json
import os
from pathlib import Path
import time
from typing import Dict, Any, Optional

from config.settings import settings, Settings
from .acceptance import (
    AcceptanceState,
    RuntimeManifest,
    evaluate_duration_gate,
    GateEvaluationResult,
    MIN_24H_SECONDS,
    MIN_72H_SECONDS,
)
from .fingerprint import compute_config_fingerprint
from .metrics import QualityMetricsCollector


def generate_quality_report(
    base_data_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    cfg: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Generate comprehensive quality and acceptance report for the current recording run."""
    c = cfg or settings
    data_dir = Path(base_data_path or c.storage.base_data_path)
    man_path = Path(manifest_path or Path("data/runtime/current_run.json"))
    out_dir = Path(output_dir or Path("data/quality"))
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: Optional[RuntimeManifest] = None
    if man_path.exists():
        try:
            manifest = RuntimeManifest.load(man_path)
        except Exception:
            manifest = None

    collector = QualityMetricsCollector(base_data_path=data_dir, cfg=c)

    # 1. Health metrics
    health = collector.collect_health_metrics(manifest)
    elapsed_seconds = health.elapsed_seconds

    # 2. Storage metrics
    storage = collector.collect_storage_metrics(elapsed_seconds=elapsed_seconds)

    # 3. DuckDB query metrics (timestamps & feeds)
    integrity, venue_feeds = collector.collect_duckdb_metrics()

    # 4. Coverage metrics
    coverage = collector.collect_coverage_metrics(venue_feeds)

    # 4b. Stream continuity & data span metrics across required feeds
    since_ts_ns = None
    if manifest and getattr(manifest, "started_at_utc", None):
        try:
            from datetime import datetime
            st_dt = datetime.fromisoformat(manifest.started_at_utc.replace("Z", "+00:00"))
            since_ts_ns = int(st_dt.timestamp() * 1e9)
        except Exception:
            since_ts_ns = None

    stream_continuity = collector.collect_stream_continuity_metrics(
        since_ts_ns=since_ts_ns,
        current_time_s=time.time(),
    )

    # 5. Invariant criteria assessment for gates
    hard_failure_reasons = []
    observational_notes = []
    
    if not storage.manifest_valid:
        hard_failure_reasons.append(f"Storage manifest verification failed: {storage.manifest_errors}")
    if storage.orphan_tmp_files > 0:
        hard_failure_reasons.append(f"Orphan .tmp files detected in storage: {storage.orphan_tmp_files}")
    if integrity.true_causal_violations > 0:
        hard_failure_reasons.append(
            f"True causal timestamp violation: {integrity.true_causal_violations} events occurred before cause after clock offset calibration."
        )
    if storage.parquet_file_count == 0 or storage.total_row_count == 0:
        hard_failure_reasons.append("Storage is empty: no parquet parts or rows have been committed.")

    if not stream_continuity.all_streams_pass:
        hard_failure_reasons.extend(stream_continuity.failures)

    if integrity.is_host_clock_skew_detected:
        observational_notes.append(
            f"Host clock skew detected: local OS clock is lagging exchange by ~{abs(integrity.estimated_clock_offset_ms):.1f}ms. "
            f"Corrected physical transit latency: P50={integrity.corrected_latency_p50_ms}ms, P95={integrity.corrected_latency_p95_ms}ms, P99={integrity.corrected_latency_p99_ms}ms."
        )

    if manifest and not health.is_process_alive:
        hard_failure_reasons.append("Recorder process is NOT alive (dead or terminated PID).")

    base_criteria_pass = len(hard_failure_reasons) == 0

    # 6. Evaluate 24h Gate
    gate_24h = evaluate_duration_gate(
        gate_name="24h",
        elapsed_seconds=elapsed_seconds,
        metrics_pass=base_criteria_pass and stream_continuity.all_streams_pass,
        effective_data_span_seconds=stream_continuity.effective_data_span_seconds,
        is_process_alive=health.is_process_alive if manifest else None,
        total_row_count=storage.total_row_count,
        stream_continuity_failures=list(stream_continuity.failures),
        reasons=list(hard_failure_reasons),
    )

    # 7. Evaluate 72h Gate
    gate_72h = evaluate_duration_gate(
        gate_name="72h",
        elapsed_seconds=elapsed_seconds,
        metrics_pass=base_criteria_pass and stream_continuity.all_streams_pass,
        effective_data_span_seconds=stream_continuity.effective_data_span_seconds,
        is_process_alive=health.is_process_alive if manifest else None,
        total_row_count=storage.total_row_count,
        stream_continuity_failures=list(stream_continuity.failures),
        reasons=list(hard_failure_reasons),
    )

    # Overall State determination
    if not manifest:
        overall_state = AcceptanceState.NOT_STARTED
    elif gate_72h.status == "PASS":
        overall_state = AcceptanceState.CHECKPOINT_72H_PASS
    elif gate_72h.status == "FAIL":
        overall_state = AcceptanceState.CHECKPOINT_72H_FAIL
    elif gate_24h.status == "PASS":
        overall_state = AcceptanceState.CHECKPOINT_24H_PASS
    elif gate_24h.status == "FAIL":
        overall_state = AcceptanceState.CHECKPOINT_24H_FAIL
    else:
        overall_state = AcceptanceState.RUNNING

    now_utc_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report_filename = f"acceptance_{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}.json"
    report_path = out_dir / report_filename

    report: Dict[str, Any] = {
        "report_metadata": {
            "generated_at_utc": now_utc_str,
            "report_file": report_filename,
            "overall_state": overall_state.value,
            "observational_notes": observational_notes,
        },
        "run_metadata": {
            "run_id": manifest.run_id if manifest else "UNKNOWN",
            "git_sha": manifest.git_sha if manifest else "UNKNOWN",
            "config_fingerprint": manifest.config_fingerprint if manifest else compute_config_fingerprint(c),
            "started_at_utc": manifest.started_at_utc if manifest else None,
            "venues_configured": manifest.venues if manifest else ["polymarket", "deribit", "binance_perp"],
        },
        "runtime_health": health.model_dump(),
        "storage_metrics": storage.model_dump(),
        "stream_continuity": stream_continuity.model_dump(),
        "timestamp_integrity": integrity.model_dump(),
        "venue_feeds": {k: v.model_dump() for k, v in venue_feeds.items()},
        "coverage_metrics": coverage.model_dump(),
        "gates": {
            "gate_24h": gate_24h.model_dump(),
            "gate_72h": gate_72h.model_dump(),
        },
    }

    # Write report file atomically
    tmp_out = out_dir / f".tmp_{report_filename}_{os.getpid()}"
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    os.replace(tmp_out, report_path)

    return report
