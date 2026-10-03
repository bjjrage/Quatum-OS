"""Offline unit tests for Data Quality Acceptance gates, duration gating, and metrics."""
import json
import time
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from config.settings import Settings, PolymarketConfig, DeribitConfig, BinanceFuturesConfig, StorageConfig
from src.quality.acceptance import (
    AcceptanceState,
    GateDurationError,
    evaluate_duration_gate,
    validate_state_transition,
    RuntimeManifest,
    MIN_24H_SECONDS,
    MIN_72H_SECONDS,
)
from src.quality.fingerprint import compute_config_fingerprint, canonicalize_config
from src.quality.metrics import QualityMetricsCollector
from src.quality.reporter import generate_quality_report
from src.common.manifest import PartitionManifest, compute_sha256
from src.common.types import SCHEMAS


def test_config_fingerprint_deterministic_and_sensitive_to_changes() -> None:
    """Fingerprint must be deterministic and change when config values change."""
    cfg1 = Settings()
    cfg2 = Settings()
    
    fp1 = compute_config_fingerprint(cfg1)
    fp2 = compute_config_fingerprint(cfg2)
    assert len(fp1) == 64
    assert fp1 == fp2

    # Mutate symbol list
    cfg3 = Settings(
        binance=BinanceFuturesConfig(
            initial_calibration_sample_v0=["BTCUSDT", "ETHUSDT", "NEWTOKENUSDT"]
        )
    )
    fp3 = compute_config_fingerprint(cfg3)
    assert fp3 != fp1

    # Mutate deribit parameter
    cfg4 = Settings(
        deribit=DeribitConfig(moneyness_max=1.50)
    )
    fp4 = compute_config_fingerprint(cfg4)
    assert fp4 != fp1

    # Verify no secret keywords in canonical dict
    canon = canonicalize_config(cfg1)
    serialized = json.dumps(canon)
    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "private" not in serialized


def test_duration_gating_cannot_pass_early() -> None:
    """Neither 24h nor 72h gate can pass before the required continuous elapsed time."""
    # Under 24h
    res_24_under = evaluate_duration_gate("24h", elapsed_seconds=3600.0, metrics_pass=True)
    assert res_24_under.status == "PENDING"
    assert res_24_under.passed is False
    assert any("not met" in r for r in res_24_under.reasons)

    res_72_under = evaluate_duration_gate("72h", elapsed_seconds=3600.0, metrics_pass=True)
    assert res_72_under.status == "PENDING"
    assert res_72_under.passed is False

    # Attempting to validate state transition to PASS before duration must raise GateDurationError
    with pytest.raises(GateDurationError, match="Cannot transition to CHECKPOINT_24H_PASS"):
        validate_state_transition(
            AcceptanceState.RUNNING,
            AcceptanceState.CHECKPOINT_24H_PASS,
            elapsed_seconds=86399.0,
        )

    with pytest.raises(GateDurationError, match="Cannot transition to CHECKPOINT_72H_PASS"):
        validate_state_transition(
            AcceptanceState.CHECKPOINT_24H_PASS,
            AcceptanceState.CHECKPOINT_72H_PASS,
            elapsed_seconds=259199.0,
        )


def test_duration_gating_passes_only_when_time_and_metrics_met() -> None:
    """Gates pass only when both elapsed time and metrics are satisfied."""
    # 24h satisfied, metrics satisfied
    res_24_pass = evaluate_duration_gate(
        "24h", elapsed_seconds=MIN_24H_SECONDS + 10.0, metrics_pass=True
    )
    assert res_24_pass.status == "PASS"
    assert res_24_pass.passed is True

    # 24h satisfied, metrics failed
    res_24_fail = evaluate_duration_gate(
        "24h", elapsed_seconds=MIN_24H_SECONDS + 10.0, metrics_pass=False, reasons=["Corrupt part"]
    )
    assert res_24_fail.status == "FAIL"
    assert res_24_fail.passed is False
    assert "Corrupt part" in res_24_fail.reasons

    # 72h satisfied, metrics satisfied
    res_72_pass = evaluate_duration_gate(
        "72h", elapsed_seconds=MIN_72H_SECONDS + 10.0, metrics_pass=True
    )
    assert res_72_pass.status == "PASS"
    assert res_72_pass.passed is True

    # State transition allowed when duration requirement is met
    assert validate_state_transition(
        AcceptanceState.RUNNING, AcceptanceState.CHECKPOINT_24H_PASS, elapsed_seconds=MIN_24H_SECONDS
    ) == AcceptanceState.CHECKPOINT_24H_PASS

    assert validate_state_transition(
        AcceptanceState.CHECKPOINT_24H_PASS, AcceptanceState.CHECKPOINT_72H_PASS, elapsed_seconds=MIN_72H_SECONDS
    ) == AcceptanceState.CHECKPOINT_72H_PASS


def test_runtime_manifest_lifecycle(tmp_path: Path) -> None:
    """Runtime manifest creates, saves, loads, and computes elapsed time correctly."""
    manifest_file = tmp_path / "current_run.json"
    manifest = RuntimeManifest.create_new(
        pid=12345,
        git_sha="9040ea5ff8a66f61e23b3e29680d55a2dd5be580",
        config_fingerprint="abcdef1234567890",
    )
    assert manifest.pid == 12345
    assert manifest.status == AcceptanceState.RUNNING
    assert manifest.elapsed_seconds() >= 0.0

    manifest.save(manifest_file)
    assert manifest_file.exists()

    loaded = RuntimeManifest.load(manifest_file)
    assert loaded.run_id == manifest.run_id
    assert loaded.pid == 12345
    assert loaded.git_sha == "9040ea5ff8a66f61e23b3e29680d55a2dd5be580"


def test_storage_metrics_and_manifest_checksum_verification(tmp_path: Path) -> None:
    """Storage metrics detect valid parquet files and flag corrupted checksums."""
    part_dir = tmp_path / "binance_perp" / "table=bbo_ticks" / "year=2026" / "month=10" / "day=02" / "hour=20"
    part_dir.mkdir(parents=True, exist_ok=True)
    part_file = part_dir / "part-001.parquet"

    # Create dummy parquet table
    schema = SCHEMAS["bbo_ticks"]
    table = pa.Table.from_pylist(
        [
            {
                "ts_exchange_ns": 1000000000,
                "ts_received_utc_ns": 1005000000,
                "ts_received_mono_ns": 5000000,
                "observed_event_age_ns": 5000000,
                "venue": "binance_perp",
                "symbol": "BTCUSDT",
                "bid_price": 60000.0,
                "bid_size": 1.0,
                "ask_price": 60001.0,
                "ask_size": 1.0,
                "spread": 1.0,
            }
        ],
        schema=schema,
    )
    pq.write_table(table, part_file, compression="zstd")

    # Record in manifest
    manifest = PartitionManifest(part_dir)
    sha256 = compute_sha256(part_file)
    manifest.record_part("part-001.parquet", row_count=1, byte_size=part_file.stat().st_size, sha256_hash=sha256)

    collector = QualityMetricsCollector(base_data_path=tmp_path)
    metrics = collector.collect_storage_metrics(elapsed_seconds=120.0)

    assert metrics.parquet_file_count == 1
    assert metrics.total_row_count == 1
    assert metrics.manifest_valid is True
    assert len(metrics.manifest_errors) == 0

    # Corrupt the parquet file by appending junk bytes
    with open(part_file, "ab") as f:
        f.write(b"CORRUPTED_BYTES")

    metrics_corrupt = collector.collect_storage_metrics(elapsed_seconds=120.0)
    assert metrics_corrupt.manifest_valid is False
    assert any("SHA256 mismatch" in err for err in metrics_corrupt.manifest_errors)


def test_timestamp_integrity_and_duckdb_analysis(tmp_path: Path) -> None:
    """DuckDB queries detect negative event ages (time traveler paradox)."""
    part_dir = tmp_path / "binance_perp" / "table=bbo_ticks" / "year=2026" / "month=10" / "day=02" / "hour=20"
    part_dir.mkdir(parents=True, exist_ok=True)
    part_file = part_dir / "part-002.parquet"

    schema = SCHEMAS["bbo_ticks"]
    # Row 1: Normal positive latency (age = 10ms)
    # Row 2: Negative latency (exchange ts > receive ts -> time traveler paradox!)
    rows = [
        {
            "ts_exchange_ns": 1700000000000000000,
            "ts_received_utc_ns": 1700000000010000000,
            "ts_received_mono_ns": 10000000,
            "observed_event_age_ns": 10000000,
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 60000.0,
            "bid_size": 1.0,
            "ask_price": 60001.0,
            "ask_size": 1.0,
            "spread": 1.0,
        },
        {
            "ts_exchange_ns": 1700000000050000000,
            "ts_received_utc_ns": 1700000000010000000,  # Received before exchange!
            "ts_received_mono_ns": 10000000,
            "observed_event_age_ns": -40000000,
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 60000.0,
            "bid_size": 1.0,
            "ask_price": 60001.0,
            "ask_size": 1.0,
            "spread": 1.0,
        },
    ]

    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, part_file, compression="zstd")

    collector = QualityMetricsCollector(base_data_path=tmp_path)
    integrity, feeds = collector.collect_duckdb_metrics()

    assert integrity.total_events_checked == 2
    assert integrity.negative_event_age_count == 1
    assert "binance_perp" in feeds
    assert feeds["binance_perp"].total_events == 2


def test_generate_quality_report_end_to_end(tmp_path: Path) -> None:
    """Full quality report generation produces complete schema and persists to disk."""
    data_dir = tmp_path / "raw"
    runtime_dir = tmp_path / "runtime"
    quality_dir = tmp_path / "quality"
    data_dir.mkdir()
    runtime_dir.mkdir()
    quality_dir.mkdir()

    manifest_file = runtime_dir / "current_run.json"
    manifest = RuntimeManifest.create_new(
        pid=99999,
        git_sha="9040ea5ff8a66f61e23b3e29680d55a2dd5be580",
        config_fingerprint=compute_config_fingerprint(),
    )
    manifest.save(manifest_file)

    report = generate_quality_report(
        base_data_path=data_dir,
        manifest_path=manifest_file,
        output_dir=quality_dir,
    )

    assert "report_metadata" in report
    assert "run_metadata" in report
    assert "runtime_health" in report
    assert "storage_metrics" in report
    assert "timestamp_integrity" in report
    assert "gates" in report
    assert report["gates"]["gate_24h"]["status"] == "PENDING"
    assert report["gates"]["gate_72h"]["status"] == "PENDING"

    # Verify JSON file was created
    report_files = list(quality_dir.glob("acceptance_*.json"))
    assert len(report_files) == 1
    with open(report_files[0], "r", encoding="utf-8") as f:
        loaded_report = json.load(f)
    assert loaded_report["run_metadata"]["run_id"] == manifest.run_id


def test_clock_sync_inference_and_latency_correction() -> None:
    """Infer host clock offset from raw ages and verify corrected physical transit latency."""
    from src.quality.clock_sync import infer_clock_offset_from_distribution, analyze_timestamp_latencies

    # Raw ages centered around -3500ms (local clock lagging exchange by ~3.5s)
    # with genuine transit latency ~20-80ms
    raw_ages = [-3500.0 + i * 2.0 for i in range(50)]
    
    offset = infer_clock_offset_from_distribution(raw_ages, assumed_min_transit_latency_ms=15.0)
    assert offset < -3500.0
    assert abs(offset - (-3515.0)) < 5.0

    analysis = analyze_timestamp_latencies(raw_ages)
    assert analysis.is_skew_detected is True
    assert analysis.raw_negative_count == 50
    assert analysis.corrected_p50_ms > 0.0
    assert analysis.true_causal_violations == 0


def test_clock_sync_detects_true_causal_violation() -> None:
    """Flag genuine causal paradoxes where an event claims to occur in the future beyond clock drift."""
    from src.quality.clock_sync import analyze_timestamp_latencies

    # Normal ages with offset -3500ms, plus one extreme corrupted event with age -50000ms
    raw_ages = [-3500.0] * 50 + [-50000.0]
    analysis = analyze_timestamp_latencies(raw_ages, explicit_offset_ms=-3500.0)
    assert analysis.true_causal_violations == 1


def test_clock_sync_synchronized_system_no_false_skew() -> None:
    """Synchronized hosts with normal positive network latencies report no skew."""
    from src.quality.clock_sync import analyze_timestamp_latencies

    normal_ages = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    analysis = analyze_timestamp_latencies(normal_ages)
    assert analysis.is_skew_detected is False
    assert analysis.clock_offset_ms == 0.0
    assert analysis.raw_negative_count == 0
    assert analysis.corrected_p50_ms == 35.0

