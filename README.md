# DuckDB + Parquet Local Demo

This is a runnable teaching demo for learning how DuckDB can query Parquet files directly.

The workflow:

```text
generated CSV invoice files
        -> pandas cleanup / conversion
        -> partitioned Parquet files
        -> DuckDB SQL queries
        -> optional pandas results in Python
```

The main idea is that you do not always need to load everything into pandas before asking questions. DuckDB can query Parquet files directly, including many Parquet files at once.

## What You Will Learn

- What Parquet is and why it is often better than CSV for analytics.
- How DuckDB can query Parquet files directly.
- How to convert CSV or Excel-like source data into Parquet.
- How to query multiple monthly files as one logical table.
- How partitioned folders like `month=2026-02` help organize data.
- Where pandas fits well, and where DuckDB fits better.
- Why Parquet's advantages are easier to see with larger datasets.

## Setup

The `Makefile` handles the Python virtual environment and dependencies:

```bash
make setup
```

That creates `.venv/` and installs:

- `pandas`: reads CSV/Excel and does cleanup.
- `pyarrow`: lets pandas write Parquet.
- `openpyxl`: lets pandas read `.xlsx` files.
- `duckdb`: lets Python scripts query DuckDB.

The SQL demo target uses the DuckDB command-line shell:

```bash
brew install duckdb
```

## Quick Start

Run the small demo:

```bash
make demo
```

That target:

1. Removes generated data from earlier runs.
2. Generates sample CSV invoice files.
3. Converts the CSV files to partitioned Parquet.
4. Runs a few DuckDB queries from Python.

Run the SQL file through the DuckDB CLI:

```bash
make sql
```

Under the hood, this uses:

```bash
duckdb -c ".read queries.sql"
```

To see all available targets:

```bash
make help
```

## Dataset Sizes

The default dataset is intentionally tiny so the demo is fast and easy to inspect:

```bash
make demo
```

For a clearer Parquet size comparison, use one of the larger profiles:

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

You can also customize the generated data:

```bash
make demo PROFILE=medium MONTHS=3 ROWS_PER_MONTH=50000
```

Compare CSV and Parquet storage after any run:

```bash
make sizes
```

With the tiny default dataset, Parquet may be about the same size as CSV because every Parquet file includes schema and metadata overhead. With the medium or large profile, compression and typed column storage become much more obvious.

## Project Files

```text
duckdb-parquet-demo/
├── Makefile
├── README.md
├── build_parquet.py
├── compare_storage.py
├── demo.py
├── generate_sample_data.py
├── queries.sql
└── requirements.txt
```

- `generate_sample_data.py`: creates synthetic monthly invoice CSV files.
- `build_parquet.py`: reads CSV or Excel invoice files, normalizes columns, and writes Parquet.
- `compare_storage.py`: compares CSV and Parquet file sizes and reports the Parquet compression codec.
- `queries.sql`: DuckDB SQL examples.
- `demo.py`: runs a few DuckDB queries from Python and prints pandas DataFrames.
- `Makefile`: wraps the common setup, generation, conversion, query, and cleanup commands.

Generated data is intentionally ignored by git:

```text
data/
├── raw/
│   ├── invoices_2026_01.csv
│   ├── invoices_2026_02.csv
│   └── invoices_2026_03.csv
└── parquet/
    └── invoices/
        ├── month=2026-01/
        │   └── invoices.parquet
        ├── month=2026-02/
        │   └── invoices.parquet
        └── month=2026-03/
            └── invoices.parquet
```

## Generate Raw CSV Files

`generate_sample_data.py` creates synthetic monthly invoice CSV files for the demo.

Run:

```bash
make data
```

Or choose a larger profile:

```bash
make data-medium
```

The generated rows include invoice ID, invoice date, customer, item code, item description, business unit, quantity, unit price, amount, and paid status.

## Convert Raw Files To Parquet

`build_parquet.py` converts the raw invoice files into partitioned Parquet files.

Run:

```bash
make parquet
```

That reads the raw invoice files and writes partitioned Parquet files:

```text
data/parquet/invoices/month=2026-01/invoices.parquet
data/parquet/invoices/month=2026-02/invoices.parquet
data/parquet/invoices/month=2026-03/invoices.parquet
```

The core idea in `build_parquet.py` is to use pandas for the messy edge of the workflow: read each source file, infer the month from its filename, normalize column names, clean important types, add a little source metadata, and write the result into a Hive-style partition folder such as `month=2026-02`:

```python
from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")
out_dir = Path("data/parquet/invoices")

for path in sorted(raw_dir.glob("invoices_*.csv")):
    _, year, month_num = path.stem.split("_")
    month = f"{year}-{month_num}"

    df = pd.read_csv(path)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    df["source_file"] = path.name
    df["month"] = month
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    month_dir = out_dir / f"month={month}"
    month_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(month_dir / "invoices.parquet", index=False, compression="zstd")
```

The actual script also supports Excel files and cleans a few more columns.

This uses pandas for the job it is excellent at:

```text
read source files
normalize columns
parse dates and numbers
write clean analytical data
```

The output is Parquet, which is better suited for repeated analytical queries.

## Query Parquet With DuckDB

Start DuckDB:

```bash
duckdb
```

If the prompt mentions `memory`, you are using an in-memory DuckDB session. That is fine for this demo. Any views you create in that session disappear when you exit, but your CSV and Parquet files remain on disk.

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

## Create A View

The first statement in `queries.sql` creates a view over the Parquet files:

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

If you want the view to persist between DuckDB sessions, open a database file:

```bash
duckdb demo.duckdb
```

Then create the view inside that session. The view definition is stored in `demo.duckdb`; the invoice data still stays in Parquet.

## Example Questions

Run the SQL examples:

```bash
make sql
```

Total amount by month:

```sql
SELECT
  month,
  COUNT(*) AS invoice_count,
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
LIMIT 10;
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

Business unit trend:

```sql
SELECT
  month,
  business_unit,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY month, business_unit
ORDER BY month, total_amount DESC;
```

This answers: “In each month, how much revenue came from each business unit?”

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

## Write Results Back To Parquet

`queries.sql` also demonstrates writing a query result as a new Parquet file:

```sql
COPY (
  SELECT
    month,
    customer,
    business_unit,
    SUM(amount) AS total_amount
  FROM invoices
  GROUP BY month, customer, business_unit
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
        -> clean Parquet
        -> summary Parquet
        -> dashboard or API
```

## Compare CSV And Parquet Sizes

Run:

```bash
make sizes
```

That executes `compare_storage.py`, which reports:

- row count
- number of CSV files
- number of Parquet files
- total CSV size
- total Parquet size
- CSV-to-Parquet size ratio
- Parquet compression codec

The same idea in Python is:

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

In this repo, the Parquet files are written with Zstandard compression.

## Use DuckDB From Python

`demo.py` queries the same Parquet files from Python:

```bash
make demo
```

The core pattern is:

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

1. Run `make demo-medium` and compare the CSV and Parquet sizes.
2. Run `make demo-large` and note how quickly DuckDB can aggregate the Parquet files.
3. Query only one month and compare it to querying all months.
4. Add another query to `queries.sql`.
5. Create a persistent DuckDB database file with views:

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

Normalize names in the conversion script. `build_parquet.py` does this before writing Parquet.

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

### Small Files

Tiny Parquet files can be similar in size to CSV files because the Parquet metadata overhead is visible at small scale. Use `make demo-medium` or `make demo-large` to see the storage advantage more clearly.

### Huge Result Sets

DuckDB can query large data quickly, but returning millions of rows to the terminal or to pandas can still be slow. Use `LIMIT` while exploring.

## Suggested Next Step

Run the repo with the medium dataset:

```bash
make demo-medium
make sql
make sizes
```

Then inspect the generated files under `data/raw/` and `data/parquet/`.

Once that feels natural, the next demo can be a tiny HTTP service:

```text
POST /query
  table: invoices
  filter: amount > 1000
  columns: customer, amount, month
```

That would directly connect this local DuckDB + Parquet experiment to the SDTP architecture.
