import glob
from pathlib import Path
import re
import time
from typing import Tuple, Dict, Any, List, Optional, Set
import duckdb
import psutil
from pydantic import BaseModel, Field

from config.settings import settings, Settings
from src.common.manifest import compute_sha256
from .acceptance import RuntimeManifest


class SingleStreamContinuity(BaseModel):
    """Continuity metrics for a single market data stream."""
    stream_name: str
    venue: str
    table: str
    exists: bool = False
    row_count: int = 0
    file_count: int = 0
    min_ts_ns: Optional[int] = None
    max_ts_ns: Optional[int] = None
    span_seconds: float = 0.0
    largest_gap_seconds: float = 0.0
    freshness_seconds: float = 0.0
    status: str = "PENDING"  # PASS | FAIL_MISSING | FAIL_GAP | FAIL_STALE | FAIL_VOLUME | FAIL_BURST
    reasons: List[str] = Field(default_factory=list)


class StreamContinuityReport(BaseModel):
    """Aggregate continuity evaluation across all required streams."""
    streams: Dict[str, SingleStreamContinuity] = Field(default_factory=dict)
    effective_data_span_seconds: float = 0.0
    overlap_min_ts_ns: Optional[int] = None
    overlap_max_ts_ns: Optional[int] = None
    all_streams_pass: bool = False
    failures: List[str] = Field(default_factory=list)


class StorageMetrics(BaseModel):
    """Storage volume, manifests, and compression performance."""
    parquet_file_count: int = 0
    total_compressed_bytes: int = 0
    total_row_count: int = 0
    bytes_per_event: float = 0.0
    projected_gb_per_day: float = 0.0
    orphan_tmp_files: int = 0
    manifest_valid: bool = True
    manifest_errors: List[str] = Field(default_factory=list)


class TimestampIntegrityMetrics(BaseModel):
    """Measurement of clock synchronization, monotonic age, and latencies."""
    negative_event_age_count: int = 0
    total_events_checked: int = 0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_min_ms: float = 0.0
    # Defensible clock skew & physical transit latency separation
    estimated_clock_offset_ms: float = 0.0
    is_host_clock_skew_detected: bool = False
    corrected_latency_p50_ms: float = 0.0
    corrected_latency_p95_ms: float = 0.0
    corrected_latency_p99_ms: float = 0.0
    true_causal_violations: int = 0


class VenueFeedMetrics(BaseModel):
    """Feed continuity and metrics for a specific venue."""
    venue: str
    total_events: int = 0
    tables: Dict[str, int] = Field(default_factory=dict)
    last_event_received_at_utc: Optional[str] = None
    unique_symbols_count: int = 0
    unique_symbols: List[str] = Field(default_factory=list)


class VenueCoverageMetrics(BaseModel):
    """Coverage of configured venues and contracts."""
    polymarket_active: bool = False
    deribit_active: bool = False
    binance_active: bool = False
    binance_oi_active: bool = False
    binance_symbols_observed: List[str] = Field(default_factory=list)
    binance_symbols_missing: List[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0


class RuntimeHealthMetrics(BaseModel):
    """Live process health and resource consumption."""
    pid: Optional[int] = None
    is_process_alive: bool = False
    rss_ram_mb: float = 0.0
    cpu_percent: float = 0.0
    elapsed_seconds: float = 0.0
    elapsed_formatted: str = "0s"


class QualityMetricsCollector:
    """Collects and aggregates quality metrics across storage, feeds, and runtime."""

    def __init__(self, base_data_path: Optional[Path] = None, cfg: Optional[Settings] = None):
        self.base_data_path = Path(base_data_path or settings.storage.base_data_path)
        self.cfg = cfg or settings

    def collect_storage_metrics(self, elapsed_seconds: float = 0.0) -> StorageMetrics:
        """Scan storage directory for parquet files, byte size, orphan tmp files, and manifests."""
        parquet_files = list(self.base_data_path.glob("**/*.parquet"))
        total_compressed_bytes = sum(f.stat().st_size for f in parquet_files)

        # Check for orphan temporary files (files only, excluding directories like .tmp/, older than 120s)
        now_ts = time.time()
        orphan_files = [
            f for f in self.base_data_path.glob("**/*.tmp")
            if f.is_file() and (now_ts - f.stat().st_mtime > 120.0)
        ]
        orphan_count = len(orphan_files)

        # Verify manifests
        manifest_files = list(self.base_data_path.glob("**/manifest.json"))
        manifest_valid = True
        manifest_errors: List[str] = []
        total_manifest_rows = 0

        for m_path in manifest_files:
            try:
                import json
                with open(m_path, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                
                parent_dir = m_path.parent
                for part in m_data.get("parts", []):
                    total_manifest_rows += part.get("row_count", 0)
                    part_file = parent_dir / part["part_filename"]
                    if not part_file.exists():
                        manifest_valid = False
                        manifest_errors.append(f"Missing file recorded in manifest: {part_file}")
                        continue
                    
                    actual_sha = compute_sha256(part_file)
                    if actual_sha != part.get("sha256"):
                        manifest_valid = False
                        manifest_errors.append(
                            f"SHA256 mismatch for {part_file.name}: expected {part.get('sha256')}, got {actual_sha}"
                        )
            except Exception as e:
                manifest_valid = False
                manifest_errors.append(f"Error reading manifest {m_path}: {e}")

        # Bytes per event
        bytes_per_event = (
            round(total_compressed_bytes / total_manifest_rows, 2)
            if total_manifest_rows > 0
            else 0.0
        )

        # Projected GB per day
        projected_gb = 0.0
        if elapsed_seconds > 60.0 and total_compressed_bytes > 0:
            bytes_per_sec = total_compressed_bytes / elapsed_seconds
            projected_gb = round((bytes_per_sec * 86400.0) / (1024.0 ** 3), 4)

        return StorageMetrics(
            parquet_file_count=len(parquet_files),
            total_compressed_bytes=total_compressed_bytes,
            total_row_count=total_manifest_rows,
            bytes_per_event=bytes_per_event,
            projected_gb_per_day=projected_gb,
            orphan_tmp_files=orphan_count,
            manifest_valid=manifest_valid,
            manifest_errors=manifest_errors,
        )

    def collect_duckdb_metrics(self) -> tuple[TimestampIntegrityMetrics, Dict[str, VenueFeedMetrics]]:
        """Query parquet files with DuckDB to extract timestamp integrity and venue distributions."""
        integrity = TimestampIntegrityMetrics()
        venue_feeds: Dict[str, VenueFeedMetrics] = {
            "polymarket": VenueFeedMetrics(venue="polymarket"),
            "deribit": VenueFeedMetrics(venue="deribit"),
            "binance_perp": VenueFeedMetrics(venue="binance_perp"),
        }

        parquet_files = list(self.base_data_path.glob("**/*.parquet"))
        if not parquet_files:
            return integrity, venue_feeds

        # Group files by (venue, table). The venue is the directory right above `table=...`:
        # attributing a table's rows/symbols to every venue that merely owns a table of that name is wrong.
        table_files: Dict[Tuple[str, str], List[str]] = {}
        for p in parquet_files:
            # path pattern: .../{venue}/table={table_name}/...
            parts = p.parts
            for idx, part in enumerate(parts):
                if part.startswith("table=") and idx > 0:
                    tbl = part.split("=", 1)[1]
                    table_files.setdefault((parts[idx - 1], tbl), []).append(p.as_posix())
                    break

        con = duckdb.connect()

        total_neg_age = 0
        total_checked = 0
        all_ages_ms: List[float] = []

        all_p50: List[float] = []
        all_p95: List[float] = []
        all_p99: List[float] = []
        all_min: List[float] = []
        all_max: List[float] = []

        for (venue_name, tbl), files in table_files.items():
            if not files:
                continue

            try:
                # 1. Row counts / freshness for this exact (venue, table)
                columns = [c[0] for c in con.execute(
                    f"DESCRIBE SELECT * FROM read_parquet({files}, union_by_name=true) LIMIT 1").fetchall()]
                ts_col = next((c for c in ("ts_received_utc_ns", "ts_polled_utc_ns") if c in columns), None)
                max_expr = f"MAX({ts_col})" if ts_col else "NULL"
                row_count, max_rx = con.execute(
                    f"SELECT COUNT(*), {max_expr} FROM read_parquet({files}, union_by_name=true)"
                ).fetchone()
                if venue_name in venue_feeds:
                    venue_feeds[venue_name].total_events += row_count
                    venue_feeds[venue_name].tables[tbl] = row_count
                    if max_rx:
                        venue_feeds[venue_name].last_event_received_at_utc = time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(max_rx / 1e9)
                        )


                # Distinct symbols, attributed ONLY to this venue (deribit_metrics uses instrument_name)
                sym_col = "symbol" if "symbol" in columns else ("instrument_name" if "instrument_name" in columns else None)
                if sym_col and venue_name in venue_feeds:
                    syms = [r[0] for r in con.execute(f"SELECT DISTINCT {sym_col} FROM read_parquet({files})").fetchall() if r[0]]
                    existing = set(venue_feeds[venue_name].unique_symbols)
                    existing.update(syms)
                    venue_feeds[venue_name].unique_symbols = sorted(existing)
                    venue_feeds[venue_name].unique_symbols_count = len(existing)

                # 2. Check observed event age and timestamp integrity
                if "observed_event_age_ns" in columns and "ts_exchange_ns" in columns:
                    age_query = f"""
                        SELECT 
                            COUNT(*) as cnt,
                            COUNT(*) FILTER (WHERE observed_event_age_ns < 0 OR ts_received_utc_ns < ts_exchange_ns) as neg_cnt,
                            quantile_cont(observed_event_age_ns / 1000000.0, 0.50) as p50,
                            quantile_cont(observed_event_age_ns / 1000000.0, 0.95) as p95,
                            quantile_cont(observed_event_age_ns / 1000000.0, 0.99) as p99,
                            MIN(observed_event_age_ns / 1000000.0) as min_val,
                            MAX(observed_event_age_ns / 1000000.0) as max_val
                        FROM read_parquet({files})
                        WHERE ts_exchange_ns IS NOT NULL AND observed_event_age_ns IS NOT NULL
                    """
                    stats = con.execute(age_query).fetchone()
                    if stats and stats[0] > 0:
                        total_checked += stats[0]
                        total_neg_age += stats[1] or 0
                        if stats[2] is not None:
                            all_p50.append(float(stats[2]))
                            all_p95.append(float(stats[3]))
                            all_p99.append(float(stats[4]))
                            all_min.append(float(stats[5]))
                            all_max.append(float(stats[6]))

            except Exception:
                continue

        con.close()

        integrity.total_events_checked = total_checked
        integrity.negative_event_age_count = total_neg_age
        if all_p50:
            integrity.latency_p50_ms = round(sum(all_p50) / len(all_p50), 2)
            integrity.latency_p95_ms = round(sum(all_p95) / len(all_p95), 2)
            integrity.latency_p99_ms = round(max(all_p99), 2)
            integrity.latency_min_ms = round(min(all_min), 2)
            integrity.latency_max_ms = round(max(all_max), 2)

            # Defensible clock skew treatment
            min_observed = min(all_min)
            if min_observed < 0.0:
                offset_ms = round(min_observed - 15.0, 2)
                integrity.estimated_clock_offset_ms = offset_ms
                integrity.is_host_clock_skew_detected = True
                integrity.corrected_latency_p50_ms = max(5.0, round(integrity.latency_p50_ms - offset_ms, 2))
                integrity.corrected_latency_p95_ms = max(10.0, round(integrity.latency_p95_ms - offset_ms, 2))
                integrity.corrected_latency_p99_ms = max(20.0, round(integrity.latency_p99_ms - offset_ms, 2))
            else:
                integrity.estimated_clock_offset_ms = 0.0
                integrity.is_host_clock_skew_detected = False
                integrity.corrected_latency_p50_ms = integrity.latency_p50_ms
                integrity.corrected_latency_p95_ms = integrity.latency_p95_ms
                integrity.corrected_latency_p99_ms = integrity.latency_p99_ms

        return integrity, venue_feeds

    def collect_coverage_metrics(self, venue_feeds: Dict[str, VenueFeedMetrics]) -> VenueCoverageMetrics:
        """Evaluate coverage of sample symbols and venues against config."""
        expected_symbols = set(self.cfg.binance.initial_calibration_sample_v0)
        observed_symbols: Set[str] = set()

        binance_feed = venue_feeds.get("binance_perp")
        if binance_feed:
            observed_symbols.update(binance_feed.unique_symbols)

        observed_expected = expected_symbols.intersection(observed_symbols)
        missing_symbols = sorted(list(expected_symbols - observed_symbols))

        coverage_ratio = len(observed_expected) / len(expected_symbols) if expected_symbols else 1.0

        polymarket_feed = venue_feeds.get("polymarket")
        deribit_feed = venue_feeds.get("deribit")

        return VenueCoverageMetrics(
            polymarket_active=bool(polymarket_feed and polymarket_feed.total_events > 0),
            deribit_active=bool(deribit_feed and deribit_feed.total_events > 0),
            binance_active=bool(binance_feed and binance_feed.total_events > 0),
            binance_oi_active=bool(binance_feed and "futures_open_interest" in binance_feed.tables),
            binance_symbols_observed=sorted(list(observed_symbols)),
            binance_symbols_missing=missing_symbols,
            coverage_ratio=round(coverage_ratio, 4),
        )

    def collect_health_metrics(self, manifest: Optional[RuntimeManifest] = None) -> RuntimeHealthMetrics:
        """Inspect process execution state, CPU, RAM, and elapsed duration."""
        if not manifest:
            return RuntimeHealthMetrics()

        pid = manifest.pid
        is_alive = False
        rss_ram_mb = 0.0
        cpu_percent = 0.0

        if pid and psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                    is_alive = True
                    rss_ram_mb = round(proc.memory_info().rss / (1024.0 * 1024.0), 2)
                    cpu_percent = round(proc.cpu_percent(interval=0.1), 2)
            except Exception:
                is_alive = False

        elapsed = manifest.elapsed_seconds()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        formatted = f"{hours}h {minutes:02d}m {seconds:02d}s"

        return RuntimeHealthMetrics(
            pid=pid,
            is_process_alive=is_alive,
            rss_ram_mb=rss_ram_mb,
            cpu_percent=cpu_percent,
            elapsed_seconds=elapsed,
            elapsed_formatted=formatted,
        )

    def collect_stream_continuity_metrics(
        self,
        since_ts_ns: Optional[int] = None,
        current_time_s: Optional[float] = None,
        required_streams: Optional[List[str]] = None,
        max_gap_seconds: Optional[float] = None,
        max_freshness_seconds: Optional[float] = None,
        min_rows: Optional[int] = None,
    ) -> StreamContinuityReport:
        """Inspect and verify continuity, data spans, freshness, and gaps across required data feeds."""
        from src.quality.acceptance import (
            PROVISIONAL_REQUIRED_STREAMS,
            PROVISIONAL_MAX_STREAM_GAP_SECONDS,
            PROVISIONAL_TICK_STREAM_MAX_GAP_SECONDS,
            PROVISIONAL_MAX_FRESHNESS_SECONDS,
            PROVISIONAL_MIN_STREAM_ROWS,
        )

        req_streams = required_streams or PROVISIONAL_REQUIRED_STREAMS
        default_max_gap = max_gap_seconds if max_gap_seconds is not None else PROVISIONAL_MAX_STREAM_GAP_SECONDS
        max_freshness = max_freshness_seconds if max_freshness_seconds is not None else PROVISIONAL_MAX_FRESHNESS_SECONDS
        threshold_min_rows = min_rows if min_rows is not None else PROVISIONAL_MIN_STREAM_ROWS
        now_s = current_time_s if current_time_s is not None else time.time()

        report = StreamContinuityReport()
        part_re = re.compile(r"part-(\d+)-")

        con = None
        try:
            con = duckdb.connect()
        except Exception:
            con = None

        valid_spans: List[tuple[int, int]] = []

        for s_name in req_streams:
            venue, tbl = s_name.split("/")
            stream_dir = self.base_data_path / venue / f"table={tbl}"
            all_files = sorted(stream_dir.glob("**/*.parquet"))

            # Filter by since_ts_ns if specified
            files = []
            file_timestamps = []
            for f in all_files:
                m = part_re.search(f.name)
                ts_part = int(m.group(1)) if m else None
                if since_ts_ns is not None:
                    if ts_part is not None and ts_part < since_ts_ns:
                        continue
                files.append(f)
                if ts_part is not None:
                    file_timestamps.append(ts_part)

            stream_metric = SingleStreamContinuity(
                stream_name=s_name,
                venue=venue,
                table=tbl,
                exists=len(files) > 0,
                file_count=len(files),
            )

            if not files:
                stream_metric.status = "FAIL_MISSING"
                stream_metric.reasons.append(f"Required stream {s_name} is missing from recording storage.")
                report.failures.append(f"Required stream missing: {s_name}")
                report.streams[s_name] = stream_metric
                continue

            # Calculate largest gap between parts
            largest_gap = 0.0
            for i in range(len(file_timestamps) - 1):
                gap = (file_timestamps[i + 1] - file_timestamps[i]) / 1e9
                if gap > largest_gap:
                    largest_gap = gap
            stream_metric.largest_gap_seconds = largest_gap

            min_ts = None
            max_ts = None
            row_count = 0

            # Count rows from manifests where available
            manifests = list(stream_dir.glob("**/manifest.json"))
            if manifests:
                import json
                for m_path in manifests:
                    try:
                        with open(m_path, "r", encoding="utf-8") as f:
                            m_data = json.load(f)
                        for part in m_data.get("parts", []):
                            pname = part.get("part_filename", "")
                            m_match = part_re.search(pname)
                            if m_match and since_ts_ns is not None:
                                if int(m_match.group(1)) < since_ts_ns:
                                    continue
                            row_count += part.get("row_count", 0)
                    except Exception:
                        pass

            if con is not None:
                try:
                    f0 = files[0].as_posix()
                    f1 = files[-1].as_posix()
                    r0 = con.execute("SELECT min(ts_received_utc_ns) FROM read_parquet(?)", [[f0]]).fetchone()[0]
                    r1 = con.execute("SELECT max(ts_received_utc_ns) FROM read_parquet(?)", [[f1]]).fetchone()[0]
                    min_ts = r0
                    max_ts = r1
                    if row_count == 0:
                        rc = con.execute("SELECT count(*) FROM read_parquet(?)", [[f.as_posix() for f in files]]).fetchone()[0]
                        row_count = rc
                except Exception:
                    pass

            if min_ts is None and file_timestamps:
                min_ts = file_timestamps[0]
            if max_ts is None and file_timestamps:
                max_ts = file_timestamps[-1]

            stream_metric.row_count = row_count
            stream_metric.min_ts_ns = min_ts
            stream_metric.max_ts_ns = max_ts

            span = max(0.0, (max_ts - min_ts) / 1e9) if (min_ts is not None and max_ts is not None) else 0.0
            stream_metric.span_seconds = span

            freshness = max(0.0, now_s - (max_ts / 1e9)) if max_ts else float("inf")
            stream_metric.freshness_seconds = freshness

            # Determine max allowed gap based on stream kind
            stream_max_gap = PROVISIONAL_TICK_STREAM_MAX_GAP_SECONDS if "tick" in tbl else default_max_gap

            stream_failures = []
            if row_count < threshold_min_rows:
                stream_failures.append(f"Insufficient rows: {row_count} < {threshold_min_rows}.")
            if largest_gap > stream_max_gap:
                stream_failures.append(f"Excessive continuity gap: {largest_gap:.1f}s > max {stream_max_gap:.1f}s.")
            if freshness > max_freshness:
                stream_failures.append(f"Stale stream: last event received {freshness:.1f}s ago > max {max_freshness:.1f}s.")

            # Burst without continuity check: e.g. lots of rows in very small span in a long run
            if row_count >= threshold_min_rows and span < 60.0 and len(files) <= 2 and since_ts_ns is not None:
                run_elapsed = (now_s * 1e9 - since_ts_ns) / 1e9
                if run_elapsed > 3600.0:
                    stream_failures.append(f"Burst without continuity: {row_count} rows across only {span:.1f}s span in {run_elapsed/3600:.1f}h run.")

            if stream_failures:
                stream_metric.status = "FAIL"
                stream_metric.reasons.extend(stream_failures)
                report.failures.extend([f"Stream {s_name}: {r}" for r in stream_failures])
            else:
                stream_metric.status = "PASS"
                if min_ts is not None and max_ts is not None:
                    valid_spans.append((min_ts, max_ts))

            report.streams[s_name] = stream_metric

        # Overall effective continuous data span
        if len(report.streams) == len(req_streams) and len(valid_spans) == len(req_streams) and not report.failures:
            report.overlap_min_ts_ns = max(s[0] for s in valid_spans)
            report.overlap_max_ts_ns = min(s[1] for s in valid_spans)
            report.effective_data_span_seconds = max(0.0, (report.overlap_max_ts_ns - report.overlap_min_ts_ns) / 1e9)
            report.all_streams_pass = True
        else:
            if valid_spans:
                report.overlap_min_ts_ns = max(s[0] for s in valid_spans)
                report.overlap_max_ts_ns = min(s[1] for s in valid_spans)
                report.effective_data_span_seconds = max(0.0, (report.overlap_max_ts_ns - report.overlap_min_ts_ns) / 1e9)
            else:
                report.effective_data_span_seconds = 0.0
            report.all_streams_pass = False

        return report
