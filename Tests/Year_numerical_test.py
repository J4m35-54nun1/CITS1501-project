from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)"
sys.path.insert(0, str(BACKEND_DIR))

from data_loader import app


def test_data_endpoint_rejects_year_zero():
    response = app.test_client().get("/api/data?year=0")

    assert response.status_code == 400
    assert "Unsupported year" in response.get_json()["error"]


def test_data_endpoint_without_year_returns_all_census_years():
    response = app.test_client().get("/api/data?region_type=lga&limit=10000")

    assert response.status_code == 200
    years = {row["census_year"] for row in response.get_json()["data"]}
    assert years == {2011, 2016, 2021}
