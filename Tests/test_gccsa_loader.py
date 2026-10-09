from pathlib import Path
import sys

import pytest


LOADER_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)" / "loaders"
sys.path.insert(0, str(LOADER_DIR))

from gccsa_loader import load_all_gccsa_datasets, load_gccsa_file


DATA_DIR = Path(__file__).resolve().parents[1] / "Data (Database)"


def test_all_gccsa_files_load_clean_records_for_each_year():
    data = load_all_gccsa_datasets()

    assert set(data["census_year"]) == {2011, 2016, 2021}
    assert (data["region_type"] == "GCCSA").all()
    assert not data.isna().any().any()
    assert not data["region_name"].str.contains(
        r"^total\b|commonwealth|data is based|note:|^nsw$|^qld$|^act$",
        case=False,
        regex=True,
    ).any()
    assert not data.duplicated(["region_name", "census_year", "source_file"]).any()


@pytest.mark.parametrize(
    ("year", "indigenous", "total", "expected_proportion"),
    [
        (2011, 54744, 4391673, 1.2),
        (2016, 70135, 4823991, 1.5),
        (2021, 90939, 5231147, 1.7),
    ],
)
def test_greater_sydney_counts_and_proportion(year, indigenous, total, expected_proportion):
    file_path = DATA_DIR / "new_south_wales_4_gccsa.csv"
    data = load_gccsa_file(str(file_path))
    sydney = data.loc[
        (data["region_name"] == "Greater Sydney") & (data["census_year"] == year)
    ].iloc[0]

    assert sydney["indigenous"] == indigenous
    assert sydney["total"] == total
    assert sydney["indigenous_proportion"] == expected_proportion
