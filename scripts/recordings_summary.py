"""Summarize a local parquet recordings tree into a small Markdown report.

Usage (from repo root):
    uv run python scripts/recordings_summary.py data/raw
    uv run python scripts/recordings_summary.py data/raw_v2 -o docs/recordings_report.md

The report is a few KB, safe to commit and share, unlike the recordings themselves.
Layout assumed: <root>/<venue>/table=<table>/**/*.parquet (any depth works for counts).

Files whose header/footer is not a valid parquet magic (truncated by a crash or a
killed process) are skipped and listed, so one bad file never hides a whole table.
"""
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb

TS_HINTS = ("event_time", "exchange_ts", "ts_exchange", "timestamp", "ts", "time", "recv", "local")
TOP_GAPS = 8
MAGIC = b"PAR1"
FILE_NS = re.compile(r"part-(\d{19})-")


def is_valid_parquet(path: Path) -> bool:
    try:
        size = path.stat().st_size
        if size < 12:
            return False
        with open(path, "rb") as fh:
            head = fh.read(4)
            fh.seek(-4, 2)
            return head == MAGIC and fh.read(4) == MAGIC
    except OSError:
        return False


def file_time(path: Path) -> str:
    m = FILE_NS.search(path.name)
    if not m:
        return "?"
    return datetime.fromtimestamp(int(m.group(1)) / 1e9, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def pick_ts_column(columns: list[tuple[str, str]]) -> str | None:
    numeric = ("BIGINT", "INTEGER", "DOUBLE", "HUGEINT", "UBIGINT", "TIMESTAMP")
    for hint in TS_HINTS:
        for name, dtype in columns:
            if hint in name.lower() and dtype.upper().startswith(numeric):
                return name
    return None


def unit_divisor(col: str) -> float | None:
    low = col.lower()
    if "_ns" in low:
        return 1e9
    if "_ms" in low:
        return 1e3
    if low.endswith("_s") or "_s_" in low:
        return 1.0
    return None


def fmt_gap(raw_gap, raw_t, div) -> str:
    if div is None:
        return f"{raw_gap:,} (unidad cruda) hasta {raw_t}"
    secs = raw_gap / div
    when = datetime.fromtimestamp(raw_t / div, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    human = f"{secs / 3600:.2f} h" if secs >= 3600 else f"{secs / 60:.1f} min" if secs >= 60 else f"{secs:.2f} s"
    return f"{human} (termina {when})"


def summarize_table(con, files: list[Path]) -> dict:
    paths = [str(f).replace("\\", "/") for f in files]
    src = "read_parquet([" + ",".join(f"'{p}'" for p in paths) + "], union_by_name=true)"
    cols = [(r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()]
    rows = con.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
    out = {"cols": cols, "rows": rows, "files": len(files)}
    ts = pick_ts_column(cols)
    out["ts_col"] = ts
    if ts and rows:
        lo, hi = con.execute(f'SELECT MIN("{ts}"), MAX("{ts}") FROM {src}').fetchone()
        out["ts_min"], out["ts_max"] = lo, hi
        out["ts_nulls"] = con.execute(f'SELECT COUNT(*) FROM {src} WHERE "{ts}" IS NULL').fetchone()[0]
        out["dupe_rows"] = (
            rows - con.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {src})").fetchone()[0]
            if rows <= 20_000_000 else None
        )
        try:
            out["gaps"] = con.execute(
                f'SELECT "{ts}" AS t, "{ts}" - LAG("{ts}") OVER (ORDER BY "{ts}") AS gap '
                f'FROM {src} WHERE "{ts}" IS NOT NULL QUALIFY gap IS NOT NULL ORDER BY gap DESC LIMIT {TOP_GAPS}'
            ).fetchall()
        except Exception:
            out["gaps"] = []
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/recordings_report.md"))
    args = ap.parse_args()

    if not args.root.exists():
        raise SystemExit(f"No existe {args.root}")

    groups: dict[tuple[str, str], list[Path]] = {}
    for f in args.root.rglob("*.parquet"):
        rel = f.relative_to(args.root).parts
        venue = rel[0] if len(rel) > 1 else "-"
        table = next((p.replace("table=", "") for p in rel if p.startswith("table=")), rel[1] if len(rel) > 2 else "-")
        groups.setdefault((venue, table), []).append(f)

    con = duckdb.connect()
    sections = []
    total_rows = total_bytes = total_files = total_bad = 0
    for (venue, table), all_files in sorted(groups.items()):
        files = [f for f in all_files if is_valid_parquet(f)]
        bad = sorted(set(all_files) - set(files))
        disk_bytes = sum(f.stat().st_size for f in all_files if f.exists())
        total_bytes += disk_bytes
        total_files += len(all_files)
        total_bad += len(bad)
        head = [f"## {venue} / {table}", "",
                f"- Archivos: {len(all_files)} ({len(bad)} corruptos/truncados) | Tamaño en disco: {disk_bytes / 1e6:.1f} MB"
                f" | Tamaño medio por archivo: {disk_bytes / max(len(all_files), 1) / 1024:.1f} KB"]
        if bad:
            head.append("- Archivos corruptos (hora UTC sacada del nombre): "
                        + "; ".join(f"`{f.name[:24]}…` {file_time(f)} ({f.stat().st_size} B)" for f in bad[:10])
                        + (f" … y {len(bad) - 10} más" if len(bad) > 10 else ""))
        if not files:
            sections.append("\n".join(head) + "\n\nSin archivos válidos.\n")
            continue
        try:
            s = summarize_table(con, files)
        except Exception as e:
            sections.append("\n".join(head) + f"\n\nERROR leyendo archivos válidos: `{e}`\n")
            continue
        total_rows += s["rows"]
        head.append(f"- Filas: {s['rows']:,}")
        head.append("- Columnas: " + ", ".join(f"`{n}` {t}" for n, t in s["cols"]))
        if s.get("ts_col"):
            div = unit_divisor(s["ts_col"])
            def show(v):
                return datetime.fromtimestamp(v / div, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if div else str(v)
            head.append(f"- Columna de tiempo: `{s['ts_col']}` | desde {show(s['ts_min'])} | hasta {show(s['ts_max'])} | nulos {s['ts_nulls']}")
            if s.get("dupe_rows") is not None:
                head.append(f"- Filas duplicadas exactas: {s['dupe_rows']:,}")
            if s.get("gaps"):
                head.append("- Mayores huecos entre eventos: " + "; ".join(fmt_gap(g, t, div) for t, g in s["gaps"]))
        else:
            head.append("- No se detectó columna de tiempo numérica")
        sections.append("\n".join(head) + "\n")

    lines = [f"# Reporte de recordings: `{args.root}`", "",
             f"Total: {len(groups)} tablas, {total_files} archivos ({total_bad} corruptos), "
             f"{total_rows:,} filas válidas, {total_bytes / 1e9:.2f} GB en disco", ""] + sections
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte escrito en {args.output} ({args.output.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
