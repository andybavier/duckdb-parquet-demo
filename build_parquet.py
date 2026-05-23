from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/parquet/invoices")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def read_raw_file(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported source file: {path}")


def month_from_filename(path: Path) -> str:
    # Expected filename shape: invoices_2026_01.csv or invoices_2026_01.xlsx
    _, year, month_num = path.stem.split("_")
    return f"{year}-{month_num}"


def clean_invoice_data(df: pd.DataFrame, source_file: str, month: str) -> pd.DataFrame:
    df = normalize_columns(df)
    df["source_file"] = source_file
    df["month"] = month

    for column in ["quantity", "unit_price", "amount"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "invoice_date" in df.columns:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    if "paid" in df.columns:
        df["paid"] = df["paid"].astype(str).str.lower().map({"true": True, "false": False})

    return df


def main() -> None:
    raw_paths = sorted(
        [
            *RAW_DIR.glob("invoices_*.csv"),
            *RAW_DIR.glob("invoices_*.xlsx"),
            *RAW_DIR.glob("invoices_*.xls"),
        ]
    )

    if not raw_paths:
        raise SystemExit("No raw files found. Run `python generate_sample_data.py` first.")

    for path in raw_paths:
        month = month_from_filename(path)
        df = clean_invoice_data(read_raw_file(path), source_file=path.name, month=month)

        month_dir = OUT_DIR / f"month={month}"
        month_dir.mkdir(parents=True, exist_ok=True)

        output_path = month_dir / "invoices.parquet"
        df.to_parquet(output_path, index=False, compression="zstd")

        print(f"Wrote {output_path}: {len(df):,} rows")


if __name__ == "__main__":
    main()
