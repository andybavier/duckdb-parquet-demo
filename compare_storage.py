from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow.parquet as pq


RAW_GLOB = "data/raw/invoices_*.csv"
PARQUET_GLOB = "data/parquet/invoices/**/*.parquet"


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} GB"


def total_size(paths: list[Path]) -> int:
    return sum(path.stat().st_size for path in paths)


def parquet_compressions(paths: list[Path]) -> str:
    compressions = set()
    for path in paths:
        metadata = pq.ParquetFile(path).metadata
        for row_group_index in range(metadata.num_row_groups):
            row_group = metadata.row_group(row_group_index)
            for column_index in range(row_group.num_columns):
                compressions.add(row_group.column(column_index).compression)
    return ", ".join(sorted(compressions)) if compressions else "unknown"


def main() -> None:
    csv_paths = sorted(Path().glob(RAW_GLOB))
    parquet_paths = sorted(Path().glob(PARQUET_GLOB))

    if not csv_paths or not parquet_paths:
        raise SystemExit("Run `make parquet` first so CSV and Parquet files exist.")

    csv_size = total_size(csv_paths)
    parquet_size = total_size(parquet_paths)
    ratio = csv_size / parquet_size if parquet_size else 0

    con = duckdb.connect()
    row_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning = true)
        """
    ).fetchone()[0]

    print("Storage comparison")
    print("==================")
    print(f"Rows:             {row_count:,}")
    print(f"CSV files:        {len(csv_paths):,}")
    print(f"Parquet files:    {len(parquet_paths):,}")
    print(f"CSV total:        {human_size(csv_size)}")
    print(f"Parquet total:    {human_size(parquet_size)}")
    print(f"CSV / Parquet:    {ratio:,.2f}x")
    print(f"Parquet codec:    {parquet_compressions(parquet_paths)}")


if __name__ == "__main__":
    main()
