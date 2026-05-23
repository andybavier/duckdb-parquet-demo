from __future__ import annotations

import duckdb


PARQUET_GLOB = "data/parquet/invoices/**/*.parquet"


def print_query(con: duckdb.DuckDBPyConnection, title: str, sql: str) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    print(con.execute(sql).df().to_string(index=False))


def main() -> None:
    con = duckdb.connect()
    con.execute(
        f"""
        CREATE OR REPLACE VIEW invoices AS
        SELECT *
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning = true)
        """
    )

    print_query(
        con,
        "Rows By Month",
        """
        SELECT month, COUNT(*) AS invoice_count, SUM(amount) AS total_amount
        FROM invoices
        GROUP BY month
        ORDER BY month
        """,
    )

    print_query(
        con,
        "Top Customers",
        """
        SELECT customer, SUM(amount) AS total_amount
        FROM invoices
        GROUP BY customer
        ORDER BY total_amount DESC
        LIMIT 5
        """,
    )

    print_query(
        con,
        "Business Unit Trend",
        """
        SELECT month, business_unit, SUM(amount) AS total_amount
        FROM invoices
        GROUP BY month, business_unit
        ORDER BY month, total_amount DESC
        """,
    )


if __name__ == "__main__":
    main()
