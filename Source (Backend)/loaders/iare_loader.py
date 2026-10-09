import glob
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "Data (Database)"))
OUTPUT_COLUMNS = [
    "region_code",
    "region_name",
    "census_year",
    "indigenous",
    "non_indigenous",
    "not_stated",
    "total",
    "indigenous_proportion",
    "source_file",
    "region_type",
]
YEAR_COLUMN_BLOCKS = {
    2011: (2, 3, 4, 5),
    2016: (7, 8, 9, 10),
    2021: (12, 13, 14, 15),
}

if not os.path.exists(DATA_DIR):
    if glob.glob(os.path.join(BASE_DIR, "..", "..", "*.csv")):
        DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
    else:
        DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))


def clean_numeric(val):
    """Safely converts ABS counts to numbers, handling privacy flags."""
    if pd.isna(val):
        return 0

    val_str = str(val).strip().replace(",", "").lower()
    if val_str in {"p", "np", "..", "-", "", "n/a", "null"}:
        return 0

    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return 0


def _proportion(indigenous: pd.Series, total: pd.Series) -> pd.Series:
    """Calculates Indigenous people as a percentage of the regional total."""
    safe_total = total.where(total.ne(0), 1)
    return indigenous.div(safe_total).mul(100).where(total.ne(0), 0).round(1)


def load_iare_file(file_path: str) -> pd.DataFrame:
    """Parses an ABS IARE file into one row per Indigenous Area and year."""
    file_name = os.path.basename(file_path).lower()
    if "_iare" not in file_name:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df_raw = pd.read_csv(
        file_path,
        header=None,
        low_memory=False,
        encoding="utf-8-sig",
    )
    if df_raw.shape[1] <= 15:
        raise ValueError(f"Expected three year blocks in '{file_name}'.")

    is_iare_row = df_raw.iloc[:, 0].astype("string").str.match(
        r"^IARE\d+$",
        na=False,
    )
    source_rows = df_raw.loc[is_iare_row]
    if source_rows.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    region_code = source_rows.iloc[:, 0].astype("string").str.strip()
    region_name = source_rows.iloc[:, 1].astype("string").str.strip()
    areadfs = []

    for year, (indigenous_col, non_indigenous_col, not_stated_col, total_col) in (
        YEAR_COLUMN_BLOCKS.items()
    ):
        year_data = pd.DataFrame(
            {
                "region_code": region_code,
                "region_name": region_name,
                "census_year": year,
                "indigenous": source_rows.iloc[:, indigenous_col].apply(clean_numeric),
                "non_indigenous": source_rows.iloc[:, non_indigenous_col].apply(clean_numeric),
                "not_stated": source_rows.iloc[:, not_stated_col].apply(clean_numeric),
                "total": source_rows.iloc[:, total_col].apply(clean_numeric),
            }
        )
        year_data["indigenous_proportion"] = _proportion(
            year_data["indigenous"],
            year_data["total"],
        )
        year_data["source_file"] = file_name
        year_data["region_type"] = "IARE"
        areadfs.append(year_data[OUTPUT_COLUMNS])

    return pd.concat(areadfs, ignore_index=True)


def load_all_iare_datasets() -> pd.DataFrame:
    """Scans DATA_DIR for IARE CSV files and combines all regions and years."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*_iare.csv")))

    if not files:
        files = [
            file_path
            for file_path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
            if "_iare" in os.path.basename(file_path).lower()
        ]

    if not files:
        raise FileNotFoundError(f"No IARE census CSV files found in: {DATA_DIR}")

    areadfs = []
    for file_path in files:
        try:
            data = load_iare_file(file_path)
            if not data.empty:
                areadfs.append(data)
        except Exception as exc:
            print(
                f"Error parsing IARE file "
                f"'{os.path.basename(file_path)}': {exc}"
            )

    if not areadfs:
        raise ValueError("Could not successfully parse any IARE CSV datasets.")

    return pd.concat(areadfs, ignore_index=True)


if __name__ == "__main__":
    print("=== Testing IARE Data Loader ===")
    iare_master = load_all_iare_datasets()
    print(f"\nSUCCESS: Loaded {len(iare_master)} Indigenous Area records!")
    print("\nFirst 3 rows:")
    print(iare_master.head(3))
