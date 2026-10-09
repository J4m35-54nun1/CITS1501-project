import glob
import math
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "Data (Database)"))
OUTPUT_COLUMNS = [
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
    2011: (1, 2, 3, 4),
    2016: (6, 7, 8, 9),
    2021: (11, 12, 13, 14),
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


def _is_numeric(val):
    if pd.isna(val):
        return False

    try:
        return math.isfinite(float(str(val).strip().replace(",", "")))
    except ValueError:
        return False


def load_gccsa_file(file_path: str) -> pd.DataFrame:
    """Parses an ABS GCCSA file into one row per GCCSA region and year."""
    file_name = os.path.basename(file_path).lower()
    if "_gccsa" not in file_name:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df_raw = pd.read_csv(
        file_path,
        header=None,
        low_memory=False,
        encoding="utf-8-sig",
    )
    if df_raw.shape[1] <= 14:
        raise ValueError(f"Expected three year blocks in '{file_name}'.")

    count_section_rows = df_raw.apply(
        lambda row: row.astype("string").str.contains(
            "COUNT OF PERSONS",
            case=False,
            na=False,
        ).any(),
        axis=1,
    )
    proportion_section_rows = df_raw.apply(
        lambda row: row.astype("string").str.contains(
            r"PROPORTION\s*\(",
            case=False,
            na=False,
            regex=True,
        ).any(),
        axis=1,
    )
    count_rows = df_raw.index[count_section_rows]
    proportion_rows = df_raw.index[proportion_section_rows]
    if len(count_rows) == 0 or len(proportion_rows) == 0:
        raise ValueError(
            f"Could not locate count and proportion sections in '{file_name}'."
        )

    first_data_row = count_rows[0] + 1
    next_proportion_rows = proportion_rows[proportion_rows > count_rows[0]]
    if len(next_proportion_rows) == 0:
        raise ValueError(f"Could not locate the proportion section in '{file_name}'.")

    end_data_row = next_proportion_rows[0]
    source_rows = df_raw.iloc[first_data_row:end_data_row].copy()
    region_names = source_rows.iloc[:, 0].astype("string").str.strip()
    first_total_col = YEAR_COLUMN_BLOCKS[2011][3]
    is_gccsa_row = (
        region_names.notna()
        & region_names.ne("")
        & source_rows.iloc[:, first_total_col].apply(_is_numeric)
        & ~region_names.str.match(r"^total\b", case=False, na=False)
    )
    source_rows = source_rows.loc[is_gccsa_row]
    region_names = region_names.loc[is_gccsa_row]
    gccsa_dfs = []

    for year, (indigenous_col, non_indigenous_col, not_stated_col, total_col) in (
        YEAR_COLUMN_BLOCKS.items()
    ):
        year_data = pd.DataFrame(
            {
                "region_name": region_names,
                "census_year": year,
                "indigenous": source_rows.iloc[:, indigenous_col].apply(clean_numeric),
                "non_indigenous": source_rows.iloc[:, non_indigenous_col].apply(clean_numeric),
                "not_stated": source_rows.iloc[:, not_stated_col].apply(clean_numeric),
                "total": source_rows.iloc[:, total_col].apply(clean_numeric),
            }
        )
        safe_total = year_data["total"].where(year_data["total"].ne(0), 1)
        year_data["indigenous_proportion"] = (
            year_data["indigenous"]
            .div(safe_total)
            .mul(100)
            .where(year_data["total"].ne(0), 0)
            .round(1)
        )
        year_data["source_file"] = file_name
        year_data["region_type"] = "GCCSA"
        gccsa_dfs.append(year_data[OUTPUT_COLUMNS])

    if not gccsa_dfs:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.concat(gccsa_dfs, ignore_index=True)


def load_all_gccsa_datasets() -> pd.DataFrame:
    """Scans DATA_DIR for GCCSA CSV files and combines all regions and years."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*_gccsa.csv")))

    if not files:
        files = [
            file_path
            for file_path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
            if "_gccsa" in os.path.basename(file_path).lower()
        ]

    if not files:
        raise FileNotFoundError(f"No GCCSA census CSV files found in: {DATA_DIR}")

    gccsa_dfs = []
    for file_path in files:
        try:
            data = load_gccsa_file(file_path)
            if not data.empty:
                gccsa_dfs.append(data)
        except Exception as exc:
            print(
                f"Error parsing GCCSA file "
                f"'{os.path.basename(file_path)}': {exc}"
            )

    if not gccsa_dfs:
        raise ValueError("Could not successfully parse any GCCSA CSV datasets.")

    return pd.concat(gccsa_dfs, ignore_index=True)


if __name__ == "__main__":
    print("=== Testing GCCSA Data Loader ===")
    gccsa_master = load_all_gccsa_datasets()
    print(f"\nSUCCESS: Loaded {len(gccsa_master)} GCCSA records!")
    print("\nFirst 3 rows:")
    print(gccsa_master.head(3))