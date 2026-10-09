from pathlib import Path
import sys

import pandas as pd
import pytest


LOADER_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)" / "loaders"
sys.path.insert(0, str(LOADER_DIR))

from regional_loader import load_all_regional_datasets, load_regional_file


DATA_DIR = Path(__file__).resolve().parents[1] / "Data (Database)"
EXPECTED_COLUMNS = [
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


def test_all_ireg_files_load_clean_records_for_each_year():
    data = load_all_regional_datasets()

    assert data.columns.tolist() == EXPECTED_COLUMNS
    assert set(data["census_year"]) == {2011, 2016, 2021}
    assert data["region_code"].str.fullmatch(r"IREG\d{3}").all()
    assert data.groupby("census_year").size().nunique() == 1
    assert not data.isna().any().any()
    assert not data["region_name"].str.contains(
        r"^total\b|commonwealth|data is based|note:",
        case=False,
        regex=True,
    ).any()


@pytest.mark.parametrize(
    ("year", "indigenous", "total", "expected_proportion"),
    [
        (2011, 5155, 356586, 1.4),
        (2016, 6476, 396857, 1.6),
        (2021, 8908, 453890, 2.0),
    ],
)
def test_act_ireg_counts_and_derived_proportion(
    year,
    indigenous,
    total,
    expected_proportion,
):
    file_path = DATA_DIR / "australian_capital_territory_2.4_ireg.csv"
    data = load_regional_file(str(file_path))
    act = data.loc[data["census_year"] == year].iloc[0]

    assert act["region_code"] == "IREG801"
    assert act["region_name"] == "ACT"
    assert act["indigenous"] == indigenous
    assert act["total"] == total
    assert act["indigenous_proportion"] == expected_proportion
