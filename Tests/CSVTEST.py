import os
import glob
import pandas as pd
import pytest

# Absolute path resolution to locate "Data (Database)" from "Source (Backend)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Data (Database)"))

def get_all_converted_csvs() -> list[str]:
    """Helper function to discover all converted CSV files in Data (Database)."""
    pattern = os.path.join(DATA_DIR, "*.csv")
    csv_list = glob.glob(pattern)
    return sorted(csv_list)


def test_data_directory_exists():
    """Test 1: Verify the Data (Database) folder exists."""
    assert os.path.exists(DATA_DIR), f"Directory missing: {DATA_DIR}"


def test_csv_files_present():
    """Test 2: Verify at least one converted CSV file is present."""
    csv_files = get_all_converted_csvs()
    assert len(csv_files) > 0, f"No CSV files found in '{DATA_DIR}'."


@pytest.mark.parametrize("csv_path", get_all_converted_csvs())
def test_each_csv_file_validity(csv_path: str):
    """
    Test 3 (Parameterized): Runs an individual test for EVERY converted CSV file.
    Verifies that the file can be parsed by Pandas, is not empty, and has valid headers.
    """
    file_name = os.path.basename(csv_path)
    
    # 1. Check file size on disk
    assert os.path.getsize(csv_path) > 0, f"File is 0 bytes: {file_name}"
    
    # 2. Read into DataFrame
    df = pd.read_csv(csv_path)
    
    # 3. Assert DataFrame structure
    assert not df.empty, f"CSV loaded with 0 rows: {file_name}"
    assert len(df.columns) > 0, f"CSV has no column headers: {file_name}"


def test_combined_dataset_row_count():
    """
    Test 4: Verifies the total combined rows across all converted CSV files
    meets the CITS1501 rubric requirement of at least 200 records.
    """
    csv_files = get_all_converted_csvs()
    total_rows = 0

    for path in csv_files:
        df = pd.read_csv(path)
        total_rows += len(df)

    assert total_rows >= 200, f"Total combined records ({total_rows}) is below the required 200 threshold."

