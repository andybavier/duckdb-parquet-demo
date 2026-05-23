# DuckDB + Parquet Local Demo Guide

Date: May 23, 2026

## Purpose

This demo is meant to help you build intuition for a modern local analytics workflow:

```text
raw spreadsheet or CSV files
        ↓
pandas cleanup / conversion
        ↓
Parquet files
        ↓
DuckDB SQL queries
        ↓
optional pandas dashboard or notebook
```

The main idea is that you do not always need to load everything into pandas before asking questions. DuckDB can query Parquet files directly, including many Parquet files at once.

That makes this a useful stepping stone toward the larger SDTP idea:

```text
store data where it lives
describe it with metadata
query only what you need
move smaller result sets to the client
```

## What You Will Learn

By the end of the demo, you should understand:

- What Parquet is and why it is often better than CSV for analytics.
- How DuckDB can query Parquet files directly.
- How to convert Excel or CSV files into Parquet.
- How to query multiple monthly files as one logical table.
- How partitioned folders like `month=2026-02` help organize data.
- Where pandas fits well, and where DuckDB fits better.

## Recommended Folder Layout

Create a small project directory:

```text
duckdb-parquet-demo/
├── data/
│   ├── raw/
│   │   ├── invoices_2026_01.xlsx
│   │   ├── invoices_2026_02.xlsx
│   │   └── invoices_2026_03.xlsx
│   └── parquet/
│       └── invoices/
│           ├── month=2026-01/
│           │   └── invoices.parquet
│           ├── month=2026-02/
│           │   └── invoices.parquet
│           └── month=2026-03/
│               └── invoices.parquet
├── build_parquet.py
├── queries.sql
└── README.md
```

If you only have one source file, that is fine. Start with one and add more later.

## Install The Tools

On your Mac:

```bash
brew install duckdb
```

Then create a Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas pyarrow openpyxl duckdb
```

What these packages do:

- `pandas`: reads Excel/CSV and does cleanup.
- `pyarrow`: lets pandas write Parquet.
- `openpyxl`: lets pandas read `.xlsx` files.
- `duckdb`: lets Python scripts query DuckDB too, though the CLI is enough for the first pass.

## Step 1: Convert Raw Files To Parquet

Create `build_parquet.py`:

```python
from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")
out_dir = Path("data/parquet/invoices")

for path in sorted(raw_dir.glob("invoices_*.xlsx")):
    # Expected filename shape: invoices_2026_01.xlsx
    _, year, month_num = path.stem.split("_")
    month = f"{year}-{month_num}"

    df = pd.read_excel(path)

    # Normalize column names so every month has the same schema.
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Add source metadata. This is very useful for debugging later.
    df["source_file"] = path.name
    df["month"] = month

    # Example type cleanup. Adjust these to your real columns.
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    if "invoice_date" in df.columns:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    month_dir = out_dir / f"month={month}"
    month_dir.mkdir(parents=True, exist_ok=True)

    output_path = month_dir / "invoices.parquet"
    df.to_parquet(output_path, index=False, compression="zstd")

    print(f"Wrote {output_path}: {len(df):,} rows")
```

Run it:

```bash
python build_parquet.py
```

### What Just Happened

You used pandas for the job it is excellent at:

```text
read messy source files
normalize columns
parse dates and numbers
write clean data
```

The output is Parquet, which is better suited for repeated analytical queries.

## Step 2: Inspect Parquet With DuckDB

Start DuckDB:

```bash
duckdb
```

Query one file:

```sql
SELECT *
FROM read_parquet('data/parquet/invoices/month=2026-02/invoices.parquet')
LIMIT 5;
```

Query all monthly files:

```sql
SELECT *
FROM read_parquet('data/parquet/invoices/**/*.parquet', hive_partitioning = true)
LIMIT 5;
```

The `**/*.parquet` pattern means “find Parquet files recursively.”

The `hive_partitioning = true` option tells DuckDB to read folder names like:

```text
month=2026-02
```

as a column named `month`.

## Step 3: Create A View

Typing `read_parquet(...)` repeatedly gets old. Create a DuckDB view:

```sql
CREATE OR REPLACE VIEW invoices AS
SELECT *
FROM read_parquet(
  'data/parquet/invoices/**/*.parquet',
  hive_partitioning = true
);
```

Now query it like a regular table:

```sql
SELECT *
FROM invoices
LIMIT 10;
```

Important distinction:

```text
View over Parquet:
  data stays in Parquet files
  DuckDB reads files when queried

Native DuckDB table:
  data is copied into a DuckDB database file
```

For this demo, the view is more interesting because it shows “query files in place.”

## Step 4: Try Basic Questions

Adjust column names to match your data.

Total amount by month:

```sql
SELECT
  month,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY month
ORDER BY month;
```

Top customers:

```sql
SELECT
  customer,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY customer
ORDER BY total_amount DESC
LIMIT 20;
```

Monthly customer trend:

```sql
SELECT
  month,
  customer,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY month, customer
ORDER BY month, total_amount DESC;
```

Filter to one month:

```sql
SELECT
  customer,
  SUM(amount) AS total_amount
FROM invoices
WHERE month = '2026-02'
GROUP BY customer
ORDER BY total_amount DESC;
```

This last query is important. Because the files are partitioned by month, DuckDB can often avoid scanning unrelated month folders.

## Step 5: Write Results Back To Parquet

You can save a query result as a new Parquet file:

```sql
COPY (
  SELECT
    month,
    customer,
    SUM(amount) AS total_amount
  FROM invoices
  GROUP BY month, customer
)
TO 'data/parquet/customer_monthly_amount.parquet'
(FORMAT PARQUET, COMPRESSION ZSTD);
```

That result can be queried later:

```sql
SELECT *
FROM read_parquet('data/parquet/customer_monthly_amount.parquet')
ORDER BY total_amount DESC
LIMIT 20;
```

This is the beginning of a data pipeline:

```text
raw monthly files
        ↓
clean Parquet
        ↓
summary Parquet
        ↓
dashboard or API
```

## Step 6: Compare CSV And Parquet Sizes

If you have a CSV version of the same data:

```bash
ls -lh data/raw/*.csv data/parquet/invoices/**/*.parquet
```

Or in Python:

```python
from pathlib import Path

for path in Path("data").rglob("*"):
    if path.suffix in {".csv", ".xlsx", ".parquet"}:
        mb = path.stat().st_size / 1024 / 1024
        print(f"{path}: {mb:.2f} MB")
```

Parquet is usually much smaller than CSV because:

- CSV stores all values as text.
- Parquet stores typed binary columns.
- Repeated values compress well.
- Parquet commonly uses compression such as Snappy or Zstandard.

## Step 7: Use DuckDB From Python

You do not have to use the DuckDB CLI. Python can query the same Parquet files:

```python
import duckdb

con = duckdb.connect()

df = con.execute("""
    SELECT
      month,
      customer,
      SUM(amount) AS total_amount
    FROM read_parquet(
      'data/parquet/invoices/**/*.parquet',
      hive_partitioning = true
    )
    GROUP BY month, customer
    ORDER BY total_amount DESC
    LIMIT 20
""").df()

print(df)
```

This is a nice blend:

```text
DuckDB does the scan/filter/grouping
pandas receives the small result
```

That is often better than:

```text
pandas reads every file
pandas filters everything
pandas groups everything
```

## Mental Model

Think of the pieces this way:

### pandas

Best for:

- reading messy source files
- quick cleanup
- type normalization
- exploratory analysis
- charts and notebooks

Less ideal for:

- repeatedly serving queries
- scanning lots of files on every request
- acting as a shared data access layer

### Parquet

Best for:

- storing typed analytical data
- compression
- repeated reads
- column-oriented access
- interoperability with many data tools

Less ideal for:

- hand editing
- transactional updates
- one-row-at-a-time writes

### DuckDB

Best for:

- SQL over local files
- querying Parquet directly
- local analytics without a database server
- fast grouping, filtering, joining, sorting
- building derived tables

Less ideal for:

- high-concurrency transactional applications
- user-facing operational databases

## How This Connects To SDTP

This local demo is not SDTP yet. It is the query engine and storage layer that an SDTP-style service could use.

The future shape would be:

```text
SDML:
  describes tables and schemas

SDQL:
  describes filters like amount > 1000

SDTP:
  receives HTTP requests for filtered rows

DuckDB:
  executes those filters against Parquet

Parquet:
  stores the actual data
```

For example, an SDQL filter:

```json
{
  "operator": "GT",
  "column": "amount",
  "value": 1000
}
```

would compile to DuckDB SQL:

```sql
WHERE "amount" > ?
```

and only matching rows would be returned to the client.

That is the “query data where it lives” story.

## Experiments To Try

Try these after the basic demo works:

1. Add another monthly file and rerun `build_parquet.py`.
2. Query only one month and compare it to querying all months.
3. Add a derived summary Parquet file.
4. Compare CSV, Snappy Parquet, and Zstandard Parquet file sizes.
5. Create a DuckDB database file with views:

```bash
duckdb demo.duckdb
```

Then inside DuckDB:

```sql
CREATE OR REPLACE VIEW invoices AS
SELECT *
FROM read_parquet(
  'data/parquet/invoices/**/*.parquet',
  hive_partitioning = true
);
```

6. Try a join between invoices and a catalogue Parquet file:

```sql
SELECT
  i.month,
  c.business_unit,
  SUM(i.amount) AS total_amount
FROM invoices i
JOIN read_parquet('data/parquet/catalogue_items.parquet') c
  ON i.item_code = c.item_code
GROUP BY i.month, c.business_unit
ORDER BY i.month, total_amount DESC;
```

## Common Gotchas

### Inconsistent Column Names

Monthly spreadsheets often differ slightly:

```text
Amount
 amount
Invoice Amount
```

Normalize names in the conversion script.

### Inconsistent Types

One month might have numbers, another month might have currency strings. Clean them before writing Parquet.

### Dates

Parse dates explicitly:

```python
df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
```

### Spaces In Column Names

DuckDB can handle spaces if quoted:

```sql
SELECT "Gross Sales"
FROM table_name;
```

For learning, it is simpler to normalize to:

```text
gross_sales
```

### Huge Result Sets

DuckDB can query large data quickly, but returning millions of rows to the terminal or to pandas can still be slow. Use `LIMIT` while exploring.

## Suggested Next Step

Start with one familiar spreadsheet. Convert it to Parquet. Query it with DuckDB. Then split it into monthly files and query them as one table.

Once that feels natural, the next demo can be a tiny HTTP service:

```text
POST /query
  table: invoices
  filter: amount > 1000
  columns: customer, amount, month
```

That would directly connect this local DuckDB + Parquet experiment to the SDTP architecture.
