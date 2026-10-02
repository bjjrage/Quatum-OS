import duckdb
import glob

files = glob.glob("data/smoke_test/deribit/**/*.parquet", recursive=True)
print(f"Found {len(files)} deribit parquet files.")

if files:
    con = duckdb.connect()
    rel = con.execute("SELECT * FROM read_parquet('data/smoke_test/deribit/table=deribit_metrics/**/*.parquet') LIMIT 5")
    columns = [desc[0] for desc in rel.description]
    rows = rel.fetchall()
    print("\nCOLUMNS IN DERIBIT METRICS:")
    print(columns)
    print("\nSAMPLE ROWS:")
    for row in rows[:3]:
        record = dict(zip(columns, row))
        print(record)
