from pathlib import Path
import sys

import pytest


LOADER_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)" / "loaders"
sys.path.insert(0, str(LOADER_DIR))

from lga_loader import load_all_lga_datasets, load_lga_file


DATA_DIR = Path(__file__).resolve().parents[1] / "Data (Database)"
EXPECTED_COLUMNS = [
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


def test_all_lga_files_have_clean_rows_and_shared_columns():
    data = load_all_lga_datasets()

    assert data.columns.tolist() == EXPECTED_COLUMNS
    assert set(data["census_year"]) == {2011, 2016, 2021}
    assert not data.isna().any().any()
    assert not data["region_name"].str.match(r"^total\b", case=False).any()
    assert not data["region_name"].str.contains(
        r"commonwealth|data is based|note:", case=False, regex=True
    ).any()


@pytest.mark.parametrize(
    ("year", "expected_proportion"),
    [(2011, 1.4), (2016, 1.6), (2021, 2.0)],
)
def test_act_unincorporated_lga_and_proportion_are_loaded(year, expected_proportion):
    file_path = next(DATA_DIR.glob(f"australian_capital_territory_*_{year}_lga.csv"))

    data = load_lga_file(str(file_path))

    assert data["region_name"].tolist() == ["Unincorporated ACT"]
    assert data["census_year"].tolist() == [year]
    assert data["indigenous_proportion"].tolist() == [expected_proportion]
