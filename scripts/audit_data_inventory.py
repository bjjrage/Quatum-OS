"""Read-only inventory of local data files; writes only a Markdown report."""
from __future__ import annotations
import json, os, re
from collections import defaultdict
from pathlib import Path
import pyarrow.parquet as pq
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORT = ROOT / "docs" / "DATA_INVENTORY_LOCAL_2026-10-05.md"
PARTITION_RE = re.compile(r"year=(\d{4})[/\\]month=(\d{1,2})[/\\]day=(\d{1,2})(?:[/\\]hour=(\d{1,2}))?")
SAMPLE_FILES = 20

def fmt_bytes(n):
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB": return f"{value:,.1f} {unit}"
        value /= 1024

def scan(root):
    groups = defaultdict(lambda: {"files": [], "bytes": 0, "parquet": 0, "parts": [], "manifests": 0,
        "bad_manifests": 0, "manifest_rows": 0, "manifested": set(), "missing": 0, "size_mismatch": 0, "other": 0})
    file_count = 0
    for current, dirs, names in os.walk(root):
        dirs.sort(); names.sort()
        parent = Path(current)
        rel = parent.relative_to(root)
        venue = rel.parts[0] if rel.parts else "(root)"
        table = next((x.split("=",1)[1] for x in rel.parts if x.startswith("table=")), None)
        key = f"{venue}/{table}" if table else (f"{venue}/{rel.parts[1]}" if root.name == "historical" and len(rel.parts) > 1 else venue)
        for name in names:
            path = parent / name
            try: size = path.stat().st_size
            except OSError: continue
            file_count += 1
            g = groups[key]; g["files"].append(path); g["bytes"] += size
            if path.suffix.lower() == ".parquet":
                g["parquet"] += 1
                m = PARTITION_RE.search(str(path.relative_to(root)))
                if m: g["parts"].append(tuple(int(x or 0) for x in m.groups()))
            elif name == "manifest.json":
                g["manifests"] += 1
                try:
                    doc = json.loads(path.read_text(encoding="utf-8")); entries = doc["parts"]
                    if not isinstance(entries, list): raise ValueError("parts is not an array")
                    g["manifest_rows"] += int(doc.get("total_rows", sum(int(x["row_count"]) for x in entries)))
                    for part in entries:
                        filename = str(part["part_filename"]); g["manifested"].add((str(parent), filename))
                        target = parent / filename
                        if not target.is_file(): g["missing"] += 1
                        elif target.stat().st_size != int(part.get("byte_size", -1)): g["size_mismatch"] += 1
                except Exception: g["bad_manifests"] += 1
            else: g["other"] += 1
    return groups, file_count

def details(g, dataset_key):
    paths = [p for p in g["files"] if p.suffix.lower() == ".parquet"]
    orphan = [p for p in paths if (str(p.parent), p.name) not in g["manifested"]]
    orphan_rows = 0; footer_errors = 0
    for p in orphan:
        try: orphan_rows += pq.read_metadata(p).num_rows
        except Exception: footer_errors += 1
    schemas = set(); nulls = defaultdict(lambda: [0,0]); sample_rows = 0; duplicate_rows = 0; unique_rows = 0; sample_errors = 0
    event_min = event_max = None
    if paths:
        step = max(1, len(paths)//SAMPLE_FILES)
        for p in paths[::step][:SAMPLE_FILES]:
            try:
                pf = pq.ParquetFile(p); schemas.add(tuple((f.name,str(f.type)) for f in pf.schema_arrow))
                if not pf.metadata.num_row_groups: continue
                t = pf.read_row_group(0); cols = t.to_pydict(); sample_rows += t.num_rows
                for name in t.schema.names:
                    values = cols.get(name, []); nulls[name][0] += sum(v is None for v in values); nulls[name][1] += len(values)
                ts_name = next((n for n in ("ts_exchange_ns","ts_chain_s","ts_event_ns","open_time_ms","funding_time_ms","timestamp","event_ts") if n in cols), None)
                if ts_name:
                    vals = [v for v in cols[ts_name] if isinstance(v,(int,float))]
                    if vals: event_min = min(vals) if event_min is None else min(event_min,min(vals)); event_max = max(vals) if event_max is None else max(event_max,max(vals))
                seen = set()
                for i in range(t.num_rows): seen.add(json.dumps({k:cols[k][i] for k in t.schema.names},sort_keys=True,default=str,separators=(",",":")))
                duplicate_rows += t.num_rows; unique_rows += len(seen)
            except Exception: sample_errors += 1
    capture_dist = None; capture_unreadable = 0
    if dataset_key == "binance_perp/bbo_ticks":
        capture_dist = defaultdict(int)
        for p in paths:
            try:
                pf = pq.ParquetFile(p); nrows = pf.metadata.num_rows
                if "capture_source" not in pf.schema_arrow.names:
                    capture_dist["unknown"] += nrows
                else:
                    column = pf.read(columns=["capture_source"]).column("capture_source").to_pylist()
                    for value in column: capture_dist[value if value in ("websocket", "rest_fallback") else "unknown"] += 1
            except Exception: capture_unreadable += 1
        capture_dist = dict(capture_dist)
    row_count_known = not (g["missing"] or g["size_mismatch"] or footer_errors or capture_unreadable)
    row_count_known = row_count_known and len(g["manifested"])+len(orphan)==len(paths)
    return {"rows":g["manifest_rows"]+orphan_rows if row_count_known else None,"rows_known_from_good_files":g["manifest_rows"]+orphan_rows,
        "orphan_rows":orphan_rows,"footer_errors":footer_errors,"schemas":schemas,"nulls":nulls,"sample_rows":sample_rows,
        "duplicate_rows":duplicate_rows,"unique_rows":unique_rows,"sample_errors":sample_errors,"capture_dist":capture_dist,
        "capture_unreadable":capture_unreadable,"event_min":event_min,"event_max":event_max,
        "start":min(g["parts"]) if g["parts"] else None,"end":max(g["parts"]) if g["parts"] else None}

def fmt_partition(value):
    if not value: return "no partition labels"
    year, month, day, hour = value
    return f"{year:04d}-{month:02d}-{day:02d}" + (f" {hour:02d}:00 UTC" if hour else "")

def pump_timestamp_anomaly():
    paths=[str(p).replace("\\","/") for p in (DATA/"raw"/"pumpfun"/"table=pumpfun_trades").rglob("*.parquet")]
    if not paths: return None
    import duckdb
    sql="SELECT COUNT(*) total, SUM(CASE WHEN ts_chain_s < 1577836800 OR ts_chain_s > 1893456000 THEN 1 ELSE 0 END) bad, MIN(CASE WHEN ts_chain_s BETWEEN 1577836800 AND 1893456000 THEN ts_chain_s END) valid_min, MAX(CASE WHEN ts_chain_s BETWEEN 1577836800 AND 1893456000 THEN ts_chain_s END) valid_max FROM read_parquet(?, union_by_name=true)"
    total,bad,vmin,vmax=duckdb.connect(":memory:").execute(sql,[paths]).fetchone()
    return {"total":int(total or 0),"bad":int(bad or 0),"valid_min":vmin,"valid_max":vmax}

def historical_timestamp_range(key, paths):
    field={"binance_um/funding":"funding_time_ms","binance_um/klines_1h":"open_time_ms","binance_um/klines_1m":"open_time_ms"}.get(key)
    if not field: return None
    import duckdb
    files=[str(x).replace("\\","/") for x in paths if x.suffix.lower()==".parquet"]
    lo,hi=duckdb.connect(":memory:").execute(f"SELECT MIN({field}), MAX({field}) FROM read_parquet(?, union_by_name=true)",[files]).fetchone()
    if lo is None or hi is None: return None
    from datetime import datetime, timezone
    return (datetime.fromtimestamp(lo/1000,tz=timezone.utc).isoformat(),datetime.fromtimestamp(hi/1000,tz=timezone.utc).isoformat())

def main():
    sections=[]; all_bytes=0; all_files=0; all_groups=0
    for name in ("raw","historical","research"):
        root=DATA/name
        if not root.exists(): sections.append(f"### `data/{name}`\n\nABSENT locally.\n"); continue
        groups,nfiles=scan(root); size=sum(g["bytes"] for g in groups.values())
        all_bytes+=size; all_files+=nfiles; all_groups+=len(groups)
        lines=[f"### `data/{name}` — {fmt_bytes(size)}, {nfiles:,} files, {len(groups)} groups", ""]
        if name == "research":
            for key,g in sorted(groups.items()): lines.append(f"- `{key}`: {g['other']+g['parquet']:,} files, {fmt_bytes(g['bytes'])}")
            sections.append("\n".join(lines)+"\n"); continue
        lines += ["| Dataset | Partitions | Parquet | Rows | Size | Range UTC (partition path / event time) | Sampled schema | Sampled nulls | Exact duplicate estimate | Integrity |", "|---|---:|---:|---:|---:|---|---|---|---|---|"]
        for key,g in sorted(groups.items()):
            if not g["parquet"]:
                lines.append(f"| `{key}` | — | 0 | — | {fmt_bytes(g['bytes'])} | — | — | — | — | non-Parquet files only |"); continue
            d=details(g,key); coverage=f"{fmt_partition(d['start'])} \u2192 {fmt_partition(d['end'])}" if d["start"] else "no partition labels"
            if name == "historical":
                exact_range=historical_timestamp_range(key,g["files"])
                if exact_range: coverage=f"{exact_range[0]} to {exact_range[1]} (exact event-time scan)"
            unreadable=max(d["footer_errors"],d["capture_unreadable"],d["sample_errors"])
            rows=f"{d['rows']:,}" if d["rows"] is not None else f"PARTIAL: {d['rows_known_from_good_files']:,} readable rows; {unreadable} unreadable file(s)"
            schema="<br>".join(", ".join(f"{a}: {b}" for a,b in list(s)[:14])+(", …" if len(s)>14 else "") for s in sorted(d["schemas"])) or "unavailable"
            null_summary="; ".join(f"{k} {v}/{n}" for k,(v,n) in sorted(d["nulls"].items()) if v and n) or "none observed"
            dup=f"{d['duplicate_rows']-d['unique_rows']}/{d['duplicate_rows']} in {d['sample_rows']:,} sampled rows" if d['duplicate_rows'] else "unavailable"
            notes=[]
            if g["bad_manifests"]: notes.append(f"{g['bad_manifests']} corrupt manifest(s)")
            if g["missing"]: notes.append(f"{g['missing']} missing references")
            if g["size_mismatch"]: notes.append(f"{g['size_mismatch']} size mismatches")
            if d["footer_errors"] or d["capture_unreadable"]: notes.append(f"{max(d['footer_errors'],d['capture_unreadable'])} unreadable parquet(s)")
            if d["sample_errors"]: notes.append(f"{d['sample_errors']} sample row-group read error(s)")
            if d["capture_dist"] is not None: notes.append("capture_source rows: " + ", ".join(f"{k}={v:,}" for k,v in sorted(d['capture_dist'].items())) + (f"; unreadable={d['capture_unreadable']}" if d['capture_unreadable'] else ""))
            if len(d["schemas"])>1: notes.append(f"{len(d['schemas'])} sampled schema variants")
            if not notes: notes.append(f"{g['manifests']:,} manifests; reference sizes consistent")
            if d["event_min"] is not None: notes.append(f"sample ts raw units {d['event_min']}..{d['event_max']}")
            if key == "pumpfun/pumpfun_trades":
                anomaly=pump_timestamp_anomaly()
                if anomaly: notes.append(f"ts_chain_s outside plausible 2020-2030 Unix seconds: {anomaly['bad']:,}/{anomaly['total']:,}; valid range {anomaly['valid_min']}..{anomaly['valid_max']}")
            lines.append(f"| `{key}` | {g['manifests']:,} | {g['parquet']:,} | {rows} | {fmt_bytes(g['bytes'])} | {coverage} | {schema} | {null_summary} | {dup} | {'; '.join(notes)} |")
        sections.append("\n".join(lines)+"\n")
    text="# Local data inventory — 2026-10-05\n\nRead-only inventory of ignored local data. No Parquet, manifest, paper state, or recorder state was modified. Raw and historical row totals come from manifest totals plus Parquet footer counts for unmanifested parts, and are labeled partial when unreadable files prevent a complete total. Manifest JSON and referenced file sizes were checked; file checksums were not recomputed. Historical event-time ranges are exact scans of their timestamp columns. Schema, null, and exact-row-duplicate values are deterministic samples from up to 20 files per dataset (first row group), so they are not whole-dataset rates. Partition range is taken from path labels; sampled raw timestamp values use their source units and are not normalized. Pump.fun trade timestamp outliers are checked across the entire table against a broad 2020-2030 Unix-seconds window.\n\n"+"\n".join(sections)+f"\n## Totals\n\n- Files scanned: {all_files:,} across {all_groups} groups.\n- Bytes scanned: {fmt_bytes(all_bytes)} across raw, historical, and research.\n- Rows are counted from manifests and readable orphan Parquet footers. Any unreadable Parquet is reported separately and makes that dataset row count partial; no data was repaired.\n"
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(text,encoding="utf-8")
    print(REPORT); print(f"Scanned {all_files:,} files ({fmt_bytes(all_bytes)}); report written.")

if __name__ == "__main__": main()
