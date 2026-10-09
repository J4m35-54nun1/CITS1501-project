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


def load_regional_file(file_path: str) -> pd.DataFrame:
    """Parses an ABS IREG file into one row per Indigenous Region and year."""
    file_name = os.path.basename(file_path).lower()
    if "_ireg" not in file_name:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df_raw = pd.read_csv(
        file_path,
        header=None,
        low_memory=False,
        encoding="utf-8-sig",
    )
    if df_raw.shape[1] <= 15:
        raise ValueError(f"Expected three year blocks in '{file_name}'.")

    is_ireg_row = df_raw.iloc[:, 0].astype("string").str.match(
        r"^IREG\d{3}$",
        na=False,
    )
    source_rows = df_raw.loc[is_ireg_row]
    if source_rows.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    region_code = source_rows.iloc[:, 0].astype("string").str.strip()
    region_name = source_rows.iloc[:, 1].astype("string").str.strip()
    regional_dfs = []

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
        year_data["indigenous_proportion"] = (
            year_data["indigenous"]
            .div(year_data["total"].where(year_data["total"].ne(0), 1))
            .mul(100)
            .where(year_data["total"].ne(0), 0)
            .round(1)
        )
        year_data["source_file"] = file_name
        year_data["region_type"] = "Regional"
        regional_dfs.append(year_data[OUTPUT_COLUMNS])

    return pd.concat(regional_dfs, ignore_index=True)


def load_all_regional_datasets() -> pd.DataFrame:
    """Scans DATA_DIR for IREG CSV files and combines all years and regions."""
    pattern = os.path.join(DATA_DIR, "*_ireg.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        files = [
            file_path
            for file_path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
            if "_ireg" in os.path.basename(file_path).lower()
        ]

    if not files:
        raise FileNotFoundError(f"No IREG census CSV files found in: {DATA_DIR}")

    regional_dfs = []
    for file_path in files:
        try:
            data = load_regional_file(file_path)
            if not data.empty:
                regional_dfs.append(data)
        except Exception as exc:
            print(
                f"Error parsing IREG file "
                f"'{os.path.basename(file_path)}': {exc}"
            )

    if not regional_dfs:
        raise ValueError("Could not successfully parse any IREG CSV datasets.")

    return pd.concat(regional_dfs, ignore_index=True)


if __name__ == "__main__":
    print("=== Testing Regional Data Loader ===")
    regional_master = load_all_regional_datasets()
    print(f"\nSUCCESS: Loaded {len(regional_master)} regional records!")
    print("\nFirst 3 rows:")
    print(regional_master.head(3))
