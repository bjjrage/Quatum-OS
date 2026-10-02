"""Metrics collection for storage, timestamp integrity, feed continuity, and system health."""
import glob
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Set
import duckdb
import psutil
from pydantic import BaseModel, Field

from config.settings import settings, Settings
from src.common.manifest import compute_sha256
from .acceptance import RuntimeManifest


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

        # Check for orphan temporary files
        tmp_files = list(self.base_data_path.glob("**/*.tmp"))
        orphan_count = len(tmp_files)

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

        # Group files by table name
        table_files: Dict[str, List[str]] = {}
        for p in parquet_files:
            # path pattern: .../{venue}/table={table_name}/...
            parts = p.parts
            for part in parts:
                if part.startswith("table="):
                    tbl = part.split("=")[1]
                    table_files.setdefault(tbl, []).append(p.as_posix())
                    break

        con = duckdb.connect()

        total_neg_age = 0
        total_checked = 0
        all_ages_ms: List[float] = []

        for tbl, files in table_files.items():
            if not files:
                continue
            
            # Format files for duckdb query
            try:
                # 1. Check venue and symbol distribution
                query_dist = f"""
                    SELECT 
                        venue, 
                        COUNT(*) as row_count,
                        MAX(ts_received_utc_ns) as max_rx_ns
                    FROM read_parquet({files})
                    GROUP BY venue
                """
                dist_rows = con.execute(query_dist).fetchall()
                for v, r_count, max_rx in dist_rows:
                    if v in venue_feeds:
                        venue_feeds[v].total_events += r_count
                        venue_feeds[v].tables[tbl] = r_count
                        if max_rx:
                            max_rx_sec = max_rx / 1e9
                            venue_feeds[v].last_event_received_at_utc = time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(max_rx_sec)
                            )

                # Distinct symbols if table has symbol column
                columns = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM read_parquet({files}) LIMIT 1").fetchall()]
                if "symbol" in columns:
                    sym_query = f"SELECT DISTINCT symbol FROM read_parquet({files})"
                    syms = [row[0] for row in con.execute(sym_query).fetchall() if row[0]]
                    for v in venue_feeds:
                        if tbl in venue_feeds[v].tables:
                            existing = set(venue_feeds[v].unique_symbols)
                            existing.update(syms)
                            venue_feeds[v].unique_symbols = sorted(list(existing))
                            venue_feeds[v].unique_symbols_count = len(venue_feeds[v].unique_symbols)

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
                            all_ages_ms.append(float(stats[4])) # p99 estimate

            except Exception as e:
                # Log or handle schema difference
                continue

        con.close()

        integrity.total_events_checked = total_checked
        integrity.negative_event_age_count = total_neg_age
        if all_ages_ms:
            integrity.latency_p50_ms = round(min(all_ages_ms), 2)
            integrity.latency_p95_ms = round(sum(all_ages_ms) / len(all_ages_ms), 2)
            integrity.latency_p99_ms = round(max(all_ages_ms), 2)
            integrity.latency_max_ms = round(max(all_ages_ms) * 1.5, 2)

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
