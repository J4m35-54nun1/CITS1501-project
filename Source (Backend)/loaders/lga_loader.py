import os
import glob
import math
import pandas as pd

# Path setup targeting Data (Database) from Source (Backend)/loaders/
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

if not os.path.exists(DATA_DIR):
    if glob.glob(os.path.join(BASE_DIR, "..", "..", "*.csv")):
        DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
    else:
        DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))


def clean_numeric(val):
    """Safely converts ABS counts and percentages to numbers, handling privacy flags."""
    if pd.isna(val):
        return 0
    val_str = str(val).strip().replace(",", "").lower()
    if val_str in ["p", "np", "..", "-", "", "n/a", "null"]:
        return 0
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return 0


def _is_abs_value(val):
    """Checks whether a cell is an ABS count/percentage rather than table text."""
    if pd.isna(val):
        return False

    val_str = str(val).strip().replace(",", "").lower()
    if val_str in {"p", "np", "..", "-", "n/a", "null"}:
        return True

    try:
        return math.isfinite(float(val_str))
    except ValueError:
        return False


def load_lga_file(file_path: str) -> pd.DataFrame:
    """Parses an ABS LGA CSV into one row per region with a shared year-based schema."""
    file_name = os.path.basename(file_path).lower()
    
    if "_lga" not in file_name:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    file_year = None
    for y in ["2011", "2016", "2021"]:
        if y in file_name:
            file_year = y
            break

    if not file_year:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df_raw = pd.read_csv(file_path, header=None, low_memory=False, encoding="utf-8-sig")
    if df_raw.shape[1] <= 6:
        raise ValueError(f"Expected ABS count and proportion columns in '{file_name}'.")

    # ABS files have several title/header rows. LGA rows have a numeric total
    # in column 4, and the Indigenous proportion is column 6 (column 5 is blank).
    df = df_raw.iloc[:, [0, 1, 2, 3, 4, 6]].copy()
    df.columns = [
        "region_name",
        "indigenous",
        "non_indigenous",
        "not_stated",
        "total",
        "indigenous_proportion",
    ]
    df["region_name"] = df["region_name"].astype("string").str.strip()
    is_lga_row = (
        df["region_name"].notna()
        & df["region_name"].ne("")
        & df["total"].apply(_is_abs_value)
        & ~df["region_name"].str.match(r"^total\b", case=False, na=False)
    )
    df = df.loc[is_lga_row].copy()

    for col in OUTPUT_COLUMNS[2:7]:
        df[col] = df[col].apply(clean_numeric)

    df["census_year"] = int(file_year)
    df["source_file"] = file_name
    df["region_type"] = "LGA"
    return df[OUTPUT_COLUMNS]


def load_all_lga_datasets() -> pd.DataFrame:
    """Scans DATA_DIR for all LGA CSV files across states and combines them."""
    pattern = os.path.join(DATA_DIR, "*_lga.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        files = [f for f in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))) if "lga" in f.lower()]

    if not files:
        raise FileNotFoundError(f"No LGA census CSV files found in: {DATA_DIR}")

    lga_dfs = []
    for f in files:
        try:
            df = load_lga_file(f)
            if not df.empty:
                lga_dfs.append(df)
        except Exception as e:
            print(f"Error parsing LGA file '{os.path.basename(f)}': {e}")

    if not lga_dfs:
        raise ValueError("Could not successfully parse any LGA CSV datasets.")

    master_lga_df = pd.concat(lga_dfs, ignore_index=True)
    return master_lga_df


if __name__ == "__main__":
    print("=== Testing LGA Data Loader ===")
    lga_master = load_all_lga_datasets()
    print(f"\n✅ SUCCESS: Loaded {len(lga_master)} clean LGA records!")
    print("\nFirst 3 rows:")
    print(lga_master.head(3))