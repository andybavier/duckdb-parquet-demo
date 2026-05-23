from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path


RAW_DIR = Path("data/raw")

CUSTOMERS = [
    "Acme Manufacturing",
    "Bluebird Health",
    "Cactus Retail Co",
    "Desert Analytics",
    "Evergreen Foods",
    "Northstar Logistics",
    "Pioneer Labs",
    "Summit Schools",
]

ITEMS = [
    ("CONSULT-01", "Advisory hours", "Services", 180),
    ("SUPPORT-01", "Support plan", "Services", 95),
    ("LICENSE-01", "Platform license", "Software", 250),
    ("DATA-01", "Data package", "Data", 125),
    ("TRAIN-01", "Training workshop", "Education", 750),
]

PROFILES = {
    "small": {"months": 3, "rows_per_month": None},
    "medium": {"months": 6, "rows_per_month": 10_000},
    "large": {"months": 12, "rows_per_month": 100_000},
}


def random_date(year: int, month: int) -> date:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start + timedelta(days=random.randrange((end - start).days))


def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = (year * 12) + (month - 1) + offset
    return month_index // 12, (month_index % 12) + 1


def write_month(year: int, month: int, rows: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"invoices_{year}_{month:02d}.csv"

    fieldnames = [
        "Invoice ID",
        "Invoice Date",
        "Customer",
        "Item Code",
        "Item Description",
        "Business Unit",
        "Quantity",
        "Unit Price",
        "Amount",
        "Paid",
    ]

    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for invoice_number in range(1, rows + 1):
            item_code, description, business_unit, unit_price = random.choice(ITEMS)
            quantity = random.randint(1, 12)
            discount = random.choice([0, 0, 0, 0.05, 0.1])
            amount = round(quantity * unit_price * (1 - discount), 2)
            invoice_date = random_date(year, month)

            writer.writerow(
                {
                    "Invoice ID": f"INV-{year}{month:02d}-{invoice_number:04d}",
                    "Invoice Date": invoice_date.isoformat(),
                    "Customer": random.choice(CUSTOMERS),
                    "Item Code": item_code,
                    "Item Description": description,
                    "Business Unit": business_unit,
                    "Quantity": quantity,
                    "Unit Price": unit_price,
                    "Amount": amount,
                    "Paid": random.choice(["true", "true", "true", "false"]),
                }
            )

    print(f"Wrote {path}: {rows:,} rows")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample invoice CSV files.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="small",
        help="Built-in dataset size profile.",
    )
    parser.add_argument("--start-year", type=int, default=2026)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument(
        "--months",
        type=int,
        help="Number of monthly files to generate. Overrides the selected profile.",
    )
    parser.add_argument(
        "--rows-per-month",
        type=int,
        help="Rows to generate per month. Overrides the selected profile.",
    )
    parser.add_argument("--seed", type=int, default=20260523)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = PROFILES[args.profile]
    months = args.months or profile["months"]
    rows_per_month = args.rows_per_month or profile["rows_per_month"]

    if months < 1:
        raise SystemExit("--months must be at least 1")
    if not 1 <= args.start_month <= 12:
        raise SystemExit("--start-month must be between 1 and 12")

    random.seed(args.seed)

    if rows_per_month is None:
        small_rows = [75, 90, 85]
        for offset in range(months):
            rows = small_rows[offset % len(small_rows)]
            year, month = add_months(args.start_year, args.start_month, offset)
            write_month(year, month, rows)
        return

    if rows_per_month < 1:
        raise SystemExit("--rows-per-month must be at least 1")

    for offset in range(months):
        year, month = add_months(args.start_year, args.start_month, offset)
        write_month(year, month, rows_per_month)


if __name__ == "__main__":
    main()
