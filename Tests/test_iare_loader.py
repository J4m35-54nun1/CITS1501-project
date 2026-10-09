from pathlib import Path
import sys

import pytest


LOADER_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)" / "loaders"
sys.path.insert(0, str(LOADER_DIR))

from iare_loader import load_all_iare_datasets, load_iare_file


DATA_DIR = Path(__file__).resolve().parents[1] / "Data (Database)"


def test_all_iare_files_load_clean_records_for_each_year():
    data = load_all_iare_datasets()

    assert set(data["census_year"]) == {2011, 2016, 2021}
    assert data["region_code"].str.fullmatch(r"IARE\d+").all()
    assert not data.isna().any().any()
    assert not data["region_name"].str.contains(
        r"^total\b|commonwealth|data is based|note:",
        case=False,
        regex=True,
    ).any()


@pytest.mark.parametrize(
    ("year", "indigenous", "total", "expected_proportion"),
    [
        (2011, 423, 2909, 14.5),
        (2016, 443, 2679, 16.5),
        (2021, 440, 2474, 17.8),
    ],
)
def test_bogan_iare_counts_and_proportion(year, indigenous, total, expected_proportion):
    file_path = DATA_DIR / "new_south_wales_2.3_iare.csv"
    data = load_iare_file(str(file_path))
    bogan = data.loc[
        (data["region_name"] == "Bogan") & (data["census_year"] == year)
    ].iloc[0]

    assert bogan["region_code"] == "IARE101001"
    assert bogan["indigenous"] == indigenous
    assert bogan["total"] == total
    assert bogan["indigenous_proportion"] == expected_proportion
