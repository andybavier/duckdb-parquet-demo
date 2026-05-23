# DuckDB + Parquet Local Demo

This is a small runnable demo for learning how DuckDB can query Parquet files directly.

The workflow:

```text
generated CSV invoices
        -> pandas cleanup
        -> partitioned Parquet files
        -> DuckDB SQL queries
        -> optional Python results
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you want to use the DuckDB command-line shell too:

```bash
brew install duckdb
```

## Run The Demo

The shortest path is:

```bash
make demo
```

That creates the virtual environment, installs dependencies, generates raw CSV files, converts them to Parquet, and runs a few DuckDB queries from Python.

To see all available targets:

```bash
make help
```

To generate larger datasets where Parquet's compression is more obvious:

```bash
make demo-medium
make demo-large
```

The built-in profiles are:

```text
small   3 months, about 250 total rows
medium  6 months, 60,000 total rows
large   12 months, 1,200,000 total rows
```

You can also customize the generated dataset:

```bash
make demo PROFILE=medium MONTHS=3 ROWS_PER_MONTH=50000
```

After any run, compare CSV and Parquet storage:

```bash
make sizes
```

The manual steps are:

Generate three small monthly CSV files:

```bash
python generate_sample_data.py
```

Convert the CSV files to partitioned Parquet:

```bash
python build_parquet.py
```

Run a few DuckDB queries from Python:

```bash
python demo.py
```

Or open the DuckDB CLI and run the SQL file:

```bash
duckdb
.read queries.sql
```

## What To Inspect

Raw data lands here:

```text
data/raw/
```

Partitioned Parquet lands here:

```text
data/parquet/invoices/
├── month=2026-01/invoices.parquet
├── month=2026-02/invoices.parquet
└── month=2026-03/invoices.parquet
```

That `month=...` folder naming is called Hive partitioning. With:

```sql
FROM read_parquet('data/parquet/invoices/**/*.parquet', hive_partitioning = true)
```

DuckDB exposes `month` as a queryable column and can often skip folders that do not match a month filter.

## Useful Experiments

Compare file sizes:

```bash
make sizes
```

With the tiny default dataset, Parquet may be similar in size to CSV because each Parquet file carries schema and metadata overhead. With the medium profile, the compression benefit is much easier to see.

Query only one partition:

```sql
SELECT customer, SUM(amount) AS total_amount
FROM invoices
WHERE month = '2026-02'
GROUP BY customer
ORDER BY total_amount DESC;
```

Write a query result back to Parquet:

```sql
COPY (
  SELECT month, customer, SUM(amount) AS total_amount
  FROM invoices
  GROUP BY month, customer
)
TO 'data/parquet/customer_monthly_amount.parquet'
(FORMAT PARQUET, COMPRESSION ZSTD);
```

## Project Files

- `DuckDB_Parquet_Local_Demo_Guide.md`: the original teaching guide.
- `generate_sample_data.py`: creates realistic sample invoice CSVs using only the Python standard library.
- `build_parquet.py`: reads CSV or Excel invoice files, normalizes columns, and writes Parquet.
- `compare_storage.py`: compares CSV and Parquet file sizes and reports the Parquet compression codec.
- `queries.sql`: DuckDB SQL examples.
- `demo.py`: runs a few DuckDB queries from Python and prints pandas DataFrames.
