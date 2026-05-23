CREATE OR REPLACE VIEW invoices AS
SELECT *
FROM read_parquet(
  'data/parquet/invoices/**/*.parquet',
  hive_partitioning = true
);

-- Preview the typed Parquet data.
SELECT *
FROM invoices
LIMIT 10;

-- Total revenue and invoice count by month.
SELECT
  month,
  COUNT(*) AS invoice_count,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY month
ORDER BY month;

-- Top customers across all months.
SELECT
  customer,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY customer
ORDER BY total_amount DESC
LIMIT 10;

-- Monthly customer trend.
SELECT
  month,
  customer,
  SUM(amount) AS total_amount
FROM invoices
GROUP BY month, customer
ORDER BY month, total_amount DESC;

-- Partition pruning example: DuckDB can skip unrelated month folders.
SELECT
  customer,
  SUM(amount) AS total_amount
FROM invoices
WHERE month = '2026-02'
GROUP BY customer
ORDER BY total_amount DESC;

-- Write a derived summary dataset back to Parquet.
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
