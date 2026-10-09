from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)"
sys.path.insert(0, str(BACKEND_DIR))

from data_loader import OUTPUT_COLUMNS, app, load_all_datasets


def test_combined_data_normalizes_all_loader_schemas():
    data = load_all_datasets(refresh=True)

    assert data.columns.tolist() == OUTPUT_COLUMNS
    assert set(data["region_type"]) == {"LGA", "Regional", "IARE", "GCCSA", "ILOC"}
    assert set(data["census_year"]) == {2011, 2016, 2021}
    assert not data.isna().any().any()
    assert len(data) == 6348


def test_data_endpoint_filters_and_paginates():
    client = app.test_client()

    response = client.get(
        "/api/data?region_type=gccsa&year=2021&region_name=Sydney&limit=1"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["limit"] == 1
    assert len(payload["data"]) == 1
    assert payload["data"][0]["region_name"] == "Greater Sydney"
    assert payload["data"][0]["census_year"] == 2021


def test_data_endpoint_accepts_ireg_as_regional_alias():
    response = app.test_client().get("/api/data?region_type=ireg&year=2021&limit=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 37
    assert payload["data"][0]["region_type"] == "Regional"


def test_metadata_endpoint_reports_available_data():
    response = app.test_client().get("/api/metadata")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["region_types"] == ["lga", "regional", "iare", "gccsa", "iloc"]
    assert payload["census_years"] == [2011, 2016, 2021]
    assert payload["total_records"] == 6348


def test_states_endpoint_provides_all_state_and_census_year_summaries():
    response = app.test_client().get("/api/states")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) == 24
    assert {row["state_name"] for row in payload["data"]} == {
        "Australian Capital Territory",
        "New South Wales",
        "Northern Territory",
        "Queensland",
        "South Australia",
        "Tasmania",
        "Victoria",
        "Western Australia",
    }
    assert all(
        {"indigenous", "non_indigenous", "not_stated", "total", "indigenous_proportion"}
        <= row.keys()
        for row in payload["data"]
    )


def test_lga_data_endpoint_can_filter_to_one_state():
    response = app.test_client().get(
        "/api/data?region_type=lga&state=New%20South%20Wales&year=2021"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 129
    assert all("new_south_wales" in row["source_file"] for row in payload["data"])


def test_frontend_routes_serve_page_and_boundary_asset():
    client = app.test_client()

    page_response = client.get("/")
    boundary_response = client.head("/assets/australia_boundaries_2021.json")

    assert page_response.status_code == 200
    assert b"First Peoples" in page_response.data
    assert boundary_response.status_code == 200
    assert int(boundary_response.headers["Content-Length"]) > 0


def test_data_endpoint_rejects_invalid_filters():
    client = app.test_client()

    response = client.get("/api/data?region_type=unknown")

    assert response.status_code == 400
    assert "Unsupported region_type" in response.get_json()["error"]

def test_state_summaries_include_each_state_for_each_year():
    payload = app.test_client().get("/api/states").get_json()
    pairs = {
        (row["state_name"], row["census_year"])
        for row in payload["data"]
    }

    expected_states = {
        "Australian Capital Territory",
        "New South Wales",
        "Northern Territory",
        "Queensland",
        "South Australia",
        "Tasmania",
        "Victoria",
        "Western Australia",
    }
    expected = {
        (state, year)
        for state in expected_states
        for year in (2011, 2016, 2021)
    }

    assert pairs == expected
