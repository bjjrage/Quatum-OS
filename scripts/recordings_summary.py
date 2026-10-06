"""Summarize a local parquet recordings tree into a small Markdown report.

Usage (from repo root):
    uv run python scripts/recordings_summary.py data/raw
    uv run python scripts/recordings_summary.py data/raw_v2 -o docs/recordings_report.md

The report is a few KB, safe to commit and share, unlike the recordings themselves.
Layout assumed: <root>/<venue>/table=<table>/**/*.parquet (any depth works for counts).
"""
import argparse
from pathlib import Path

import duckdb

TS_HINTS = ("event_time", "exchange_ts", "ts_exchange", "timestamp", "ts", "time", "recv", "local")
TOP_GAPS = 5


def pick_ts_column(columns: list[tuple[str, str]]) -> str | None:
    numeric = ("BIGINT", "INTEGER", "DOUBLE", "HUGEINT", "UBIGINT", "TIMESTAMP")
    for hint in TS_HINTS:
        for name, dtype in columns:
            if hint in name.lower() and dtype.upper().startswith(numeric):
                return name
    return None


def summarize_table(con, files: list[Path]) -> dict:
    paths = [str(f).replace("\\", "/") for f in files]
    src = "read_parquet([" + ",".join(f"'{p}'" for p in paths) + "], union_by_name=true)"
    cols = [(r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()]
    rows = con.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
    out = {"cols": cols, "rows": rows, "bytes": sum(f.stat().st_size for f in files), "files": len(files)}
    ts = pick_ts_column(cols)
    out["ts_col"] = ts
    if ts and rows:
        lo, hi = con.execute(f'SELECT MIN("{ts}"), MAX("{ts}") FROM {src}').fetchone()
        out["ts_min"], out["ts_max"] = lo, hi
        out["ts_nulls"] = con.execute(f'SELECT COUNT(*) FROM {src} WHERE "{ts}" IS NULL').fetchone()[0]
        out["dupe_rows"] = rows - con.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {src})").fetchone()[0] if rows <= 20_000_000 else None
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
    lines = [f"# Reporte de recordings: `{args.root}`", ""]
    total_rows = total_bytes = 0
    sections = []
    for (venue, table), files in sorted(groups.items()):
        try:
            s = summarize_table(con, files)
        except Exception as e:
            sections.append(f"## {venue} / {table}\n\nERROR leyendo: `{e}` ({len(files)} archivos)\n")
            continue
        total_rows += s["rows"]
        total_bytes += s["bytes"]
        sec = [f"## {venue} / {table}", "",
               f"- Archivos: {s['files']} | Filas: {s['rows']:,} | Tamaño: {s['bytes'] / 1e6:.1f} MB",
               f"- Columnas: " + ", ".join(f"`{n}` {t}" for n, t in s["cols"])]
        if s.get("ts_col"):
            sec.append(f"- Columna de tiempo: `{s['ts_col']}` | min `{s['ts_min']}` | max `{s['ts_max']}` | nulos {s['ts_nulls']}")
            if s.get("dupe_rows") is not None:
                sec.append(f"- Filas duplicadas exactas: {s['dupe_rows']:,}")
            if s.get("gaps"):
                sec.append(f"- Mayores huecos (unidad de la columna): " + "; ".join(f"{g:,} en {t}" for t, g in s["gaps"]))
        else:
            sec.append("- No se detectó columna de tiempo numérica")
        sections.append("\n".join(sec) + "\n")

    lines += [f"Total: {len(groups)} tablas, {sum(len(v) for v in groups.values())} archivos, "
              f"{total_rows:,} filas, {total_bytes / 1e9:.2f} GB", ""] + sections
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte escrito en {args.output} ({args.output.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
