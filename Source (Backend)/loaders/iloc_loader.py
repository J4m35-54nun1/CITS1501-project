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
    if pd.isna(val):
        return False
    val_str = str(val).strip().replace(",", "").lower()
    if val_str in {"p", "np", "..", "-", "n/a", "null"}:
        return True
    try:
        return math.isfinite(float(val_str))
    except ValueError:
        return False

def load_iloc_file(file_path: str) -> pd.DataFrame:
    file_name = os.path.basename(file_path).lower()
    
    if "_iloc" not in file_name:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df_raw = pd.read_csv(file_path, header=None, low_memory=False, encoding="utf-8-sig")
    
    # ILOC files map all 3 years horizontally.
    # Col 1: ILOC Name
    # Cols 2-5: 2011 Data
    # Cols 7-10: 2016 Data
    # Cols 12-15: 2021 Data
    year_mappings = {
        2011: [1, 2, 3, 4, 5],
        2016: [1, 7, 8, 9, 10],
        2021: [1, 12, 13, 14, 15]
    }
    
    all_years_df = []
    
    for year, cols in year_mappings.items():
        # Prevent errors if a file is truncated or missing columns
        if max(cols) >= df_raw.shape[1]:
            continue
            
        df_year = df_raw.iloc[:, cols].copy()
        df_year.columns = [
            "region_name",
            "indigenous",
            "non_indigenous",
            "not_stated",
            "total",
        ]
        
        df_year["region_name"] = df_year["region_name"].astype("string").str.strip()
        
        # Filter out header text and keep only genuine data rows
        is_valid_row = (
            df_year["region_name"].notna()
            & df_year["region_name"].ne("")
            & df_year["total"].apply(_is_abs_value)
            & ~df_year["region_name"].str.match(r"^(total|indigenous location)", case=False, na=False)
        )
        df_year = df_year.loc[is_valid_row].copy()
        
        for col in ["indigenous", "non_indigenous", "not_stated", "total"]:
            df_year[col] = df_year[col].apply(clean_numeric)
            
        # Calculate Indigenous proportion since it is missing in the ILOC raw files
        df_year["indigenous_proportion"] = df_year.apply(
            lambda row: (row["indigenous"] / row["total"] * 100) if row["total"] > 0 else 0, 
            axis=1
        )
        
        df_year["census_year"] = year
        df_year["source_file"] = file_name
        df_year["region_type"] = "ILOC"
        
        all_years_df.append(df_year[OUTPUT_COLUMNS])

    if not all_years_df:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
        
    return pd.concat(all_years_df, ignore_index=True)

def load_all_iloc_datasets() -> pd.DataFrame:
    pattern = os.path.join(DATA_DIR, "*_iloc.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        files = [f for f in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))) if "iloc" in f.lower()]

    if not files:
        raise FileNotFoundError(f"No ILOC census CSV files found in: {DATA_DIR}")

    iloc_dfs = []
    for f in files:
        try:
            df = load_iloc_file(f)
            if not df.empty:
                iloc_dfs.append(df)
        except Exception as e:
            print(f"Error parsing ILOC file '{os.path.basename(f)}': {e}")

    if not iloc_dfs:
        raise ValueError("Could not successfully parse any ILOC CSV datasets.")

    master_iloc_df = pd.concat(iloc_dfs, ignore_index=True)
    return master_iloc_df

if __name__ == "__main__":
    print("=== Testing ILOC Data Loader ===")
    iloc_master = load_all_iloc_datasets()
    print(f"\n✅ SUCCESS: Loaded {len(iloc_master)} clean ILOC records!")
    print("\nFirst 3 rows:")
    print(iloc_master.head(3))
