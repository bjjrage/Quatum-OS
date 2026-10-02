"""Data verification utility using DuckDB to inspect collected Parquet Lakehouse partitions."""
import argparse
import sys
from pathlib import Path
import duckdb


def verify_lakehouse(base_dir: Path) -> None:
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist.")
        sys.exit(1)

    con = duckdb.connect()
    parquet_files = list(base_dir.glob("**/*.parquet"))
    print("\n" + "=" * 90)
    print(f"LAKEHOUSE VERIFICATION REPORT: {base_dir.absolute()}")
    print(f"Total Parquet part files found: {len(parquet_files)}")
    print("=" * 90)

    if not parquet_files:
        print("No parquet files to analyze.")
        return

    venues = [d.name for d in base_dir.iterdir() if d.is_dir() and d.name != ".tmp"]
    grand_total_rows = 0
    grand_total_bytes = 0

    print(f"{'VENUE':<15} | {'TABLE':<28} | {'PARTS':<8} | {'ROWS':<10} | {'SIZE (KB)':<10}")
    print("-" * 90)

    for venue in venues:
        venue_dir = base_dir / venue
        table_dirs = [td.name.replace("table=", "") for td in venue_dir.iterdir() if td.is_dir()]
        for table in table_dirs:
            glob_path = str(venue_dir / f"table={table}/**/*.parquet").replace("\\", "/")
            files = list((venue_dir / f"table={table}").glob("**/*.parquet"))
            total_bytes = sum(f.stat().st_size for f in files)
            try:
                row_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{glob_path}')").fetchone()[0]
                grand_total_rows += row_count
                grand_total_bytes += total_bytes
                size_kb = round(total_bytes / 1024, 1)
                print(f"{venue:<15} | {table:<28} | {len(files):<8} | {row_count:<10} | {size_kb:<10}")
            except Exception as e:
                print(f"{venue:<15} | {table:<28} | ERROR: {e}")

    print("=" * 90)
    print(f"GRAND TOTAL: {grand_total_rows} rows | {round(grand_total_bytes / (1024*1024), 2)} MB")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Parquet Lakehouse partitions.")
    parser.add_argument("--dir", type=str, default="data/raw", help="Base directory to inspect (default: data/raw)")
    args = parser.parse_args()
    verify_lakehouse(Path(args.dir))
