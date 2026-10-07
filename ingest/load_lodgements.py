"""
load_lodgements.py

Downloads NSW Fair Trading rental bond lodgement files and lands
each one as a Parquet file in data/raw/lodgements/.

Raw layer rules:
- Every value lands as text — no casting, no type conversion
- Nothing is deleted or filtered
- Re-runs are idempotent — same input produces same output
"""

import hashlib
import csv
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
LANDING_DIR = ROOT / "data" / "landing"
RAW_DIR     = ROOT / "data" / "raw" / "lodgements"
SOURCES     = ROOT / "ingest" / "sources.csv"

# ── Column keyword map ────────────────────────────────────────────────────────
COLUMN_MAP = {
    "postcode":        "postcode",
    "post code":       "postcode",
    "dwelling":        "dwelling_type",
    "dwelling type":   "dwelling_type", 
    "type":            "dwelling_type",
    "bedroom":         "bedrooms",
    "bedrooms":        "bedrooms",
    "weekly rent":     "weekly_rent",
    "rent":            "weekly_rent",
    "rent ($)":        "weekly_rent",
    "lodgement date":  "lodgement_date",
    "date":            "lodgement_date",
}

REQUIRED_COLUMNS = {"postcode", "dwelling_type", "bedrooms",
                    "weekly_rent", "lodgement_date"}


def sha256(path: Path) -> str:
    """Return the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_header_row(path: Path) -> int:
    preview = pd.read_excel(path, header=None, nrows=30)
    for i, row in preview.iterrows():
        row_lower = [str(v).lower().strip() for v in row]
        if any(v in ("postcode", "post code") for v in row_lower):
            return i
    raise ValueError(
        f"Could not find a header row in {path.name}.\n"
        f"First 10 rows seen:\n{preview.head(10)}"
    )


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns using COLUMN_MAP.
    Raises a clear error if a required column is missing after mapping.
    """
    rename = {}
    for col in df.columns:
        key = col.lower().strip()
        if key in COLUMN_MAP:
            rename[col] = COLUMN_MAP[key]

    df = df.rename(columns=rename)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns after mapping: {missing}\n"
            f"Columns found: {list(df.columns)}"
        )
    return df[list(REQUIRED_COLUMNS)]


def normalise(file_month: str, path: Path, source_file: str) -> pd.DataFrame:
    """
    Read one Excel file and return a clean DataFrame.
    All values are cast to string — no type conversion at this layer.
    """
    header_row = find_header_row(path)
    df = pd.read_excel(path, header=header_row, dtype=str)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = map_columns(df)

    df["file_month"]  = file_month
    df["source_file"] = source_file
    df["loaded_at"]   = datetime.now(timezone.utc).isoformat()

    return df


def process(file_month: str, url: str) -> None:
    """Download, normalise and land one month's file."""

    landing_path = LANDING_DIR / f"lodgements_{file_month}.xlsx"
    raw_path     = RAW_DIR    / f"lodgements_{file_month}.parquet"

    # ── Download ──────────────────────────────────────────────────────────────
    if landing_path.exists():
        file_hash = sha256(landing_path)
        print(f"\n[{file_month}] Using cached file  hash={file_hash[:8]}...")
    else:
        print(f"\n[{file_month}] Downloading...")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet,*/*"
            ),
            "Referer": "https://www.nsw.gov.au/housing-and-construction/"
                       "rental-forms-surveys-and-data/rental-bond-data",
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        landing_path.write_bytes(response.content)
        file_hash = sha256(landing_path)
        print(f"[{file_month}] Downloaded {len(response.content):,} bytes  hash={file_hash[:8]}...")

    # ── Normalise ─────────────────────────────────────────────────────────────
    print(f"[{file_month}] Parsing...")
    df = normalise(file_month, landing_path, landing_path.name)

    rows_in  = len(df)
    rows_out = len(df)

    # ── Write Parquet ─────────────────────────────────────────────────────────
    df.to_parquet(raw_path, index=False)
    print(f"[{file_month}] ✓  rows in={rows_in:,}  rows out={rows_out:,}  → {raw_path.name}")


def main() -> None:
    LANDING_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with open(SOURCES, newline="") as f:
        reader = csv.DictReader(f)
        sources = list(reader)

    print(f"Found {len(sources)} files to process.")

    errors = []
    for row in sources:
        try:
            process(row["file_month"], row["url"])
        except Exception as e:
            print(f"[{row['file_month']}] ERROR: {e}")
            errors.append(row["file_month"])

    print(f"\n{'─'*50}")
    print(f"Done.  {len(sources) - len(errors)}/{len(sources)} files landed successfully.")
    if errors:
        print(f"Failed: {errors}")


if __name__ == "__main__":
    main()