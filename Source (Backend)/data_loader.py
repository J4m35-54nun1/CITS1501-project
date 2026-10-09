"""Central data service for loading census CSVs and serving them to the frontend."""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, BadRequest

from loaders.gccsa_loader import load_all_gccsa_datasets
from loaders.iare_loader import load_all_iare_datasets
from loaders.iloc_loader import load_all_iloc_datasets
from loaders.lga_loader import load_all_lga_datasets
from loaders.regional_loader import load_all_regional_datasets


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "Interface (Frontend)"
OUTPUT_COLUMNS = [
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
DATASET_LOADERS = {
    "lga": load_all_lga_datasets,
    "regional": load_all_regional_datasets,
    "iare": load_all_iare_datasets,
    "gccsa": load_all_gccsa_datasets,
    "iloc": load_all_iloc_datasets,
}
AVAILABLE_YEARS = (2011, 2016, 2021)
STATE_FILE_PREFIXES = {
    "Australian Capital Territory": "australian_capital_territory_",
    "New South Wales": "new_south_wales_",
    "Northern Territory": "northern_territory_",
    "Queensland": "queensland_",
    "South Australia": "south_australia_",
    "Tasmania": "tasmania_",
    "Victoria": "victoria_",
    "Western Australia": "western_australia_",
}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


@lru_cache(maxsize=1)
def _load_combined_data() -> pd.DataFrame:
    """Load all source datasets once, then align them to the shared schema."""
    datasets = []
    for region_type, loader in DATASET_LOADERS.items():
        data = loader().copy()
        if "region_code" not in data.columns:
            data["region_code"] = ""
        data["region_code"] = data["region_code"].fillna("").astype(str)
        if "region_type" not in data.columns:
            data["region_type"] = region_type.upper()
        datasets.append(data.reindex(columns=OUTPUT_COLUMNS))

    combined = pd.concat(datasets, ignore_index=True)
    if combined.empty:
        raise ValueError("The configured census loaders returned no records.")
    if combined[OUTPUT_COLUMNS].isna().any().any():
        raise ValueError("Combined census data contains missing output values.")
    return combined


def load_all_datasets(refresh: bool = False) -> pd.DataFrame:
    """Return the combined census data; optionally reload the source CSV files."""
    if refresh:
        _load_combined_data.cache_clear()
    return _load_combined_data().copy()


def _parse_integer_query(name: str, default: int) -> int:
    value = request.args.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise BadRequest(f"Query parameter '{name}' must be an integer.") from exc


def _get_state_summaries() -> list[dict]:
    """Aggregate GCCSA subdivisions into state totals for each census year."""
    data = load_all_datasets()
    gccsa = data.loc[data["region_type"].str.lower() == "gccsa"]
    summaries = []

    for state_name, file_prefix in STATE_FILE_PREFIXES.items():
        state_rows = gccsa.loc[gccsa["source_file"].str.startswith(file_prefix)]
        for year, year_rows in state_rows.groupby("census_year", sort=True):
            indigenous = int(year_rows["indigenous"].sum())
            total = int(year_rows["total"].sum())
            summaries.append(
                {
                    "state_name": state_name,
                    "census_year": int(year),
                    "indigenous": indigenous,
                    "non_indigenous": int(year_rows["non_indigenous"].sum()),
                    "not_stated": int(year_rows["not_stated"].sum()),
                    "total": total,
                    "indigenous_proportion": (
                        round(indigenous / total * 100, 1) if total else 0
                    ),
                }
            )
    if not summaries:
        raise ValueError("No GCCSA data was available to create state summaries.")
    return summaries


@app.after_request
def add_frontend_cors_headers(response):
    """Allow browser-based frontends on another local origin to call this API."""
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    return jsonify({"error": error.description}), error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    app.logger.exception("Unhandled data service error", exc_info=error)
    return jsonify({"error": "The data service could not complete the request."}), 500


@app.get("/api/health")
def health():
    """Simple endpoint for checking that the Flask service is responding."""
    return jsonify({"status": "ok"})


@app.get("/")
def frontend():
    """Serve the interactive map application."""
    return app.send_static_file("index.html")


@app.get("/api/states")
def get_state_summaries():
    """Return state/territory counts aggregated from their GCCSA subregions."""
    return jsonify({"data": _get_state_summaries()})


@app.get("/api/metadata")
def metadata():
    """Return available region types, census years, and combined row count."""
    data = load_all_datasets()
    return jsonify(
        {
            "region_types": list(DATASET_LOADERS),
            "census_years": list(AVAILABLE_YEARS),
            "total_records": len(data),
        }
    )


@app.get("/api/data")
def get_data():
    """Return a paginated, optionally filtered set of census records."""
    region_type = request.args.get("region_type", "").strip().lower()
    if region_type == "ireg":
        region_type = "regional"
    if region_type and region_type not in DATASET_LOADERS:
        supported = ", ".join(DATASET_LOADERS)
        raise BadRequest(f"Unsupported region_type. Choose from: {supported}.")

    year_value = request.args.get("year")
    year = _parse_integer_query("year", 0)
    if year_value is not None and year not in AVAILABLE_YEARS:
        supported_years = ", ".join(map(str, AVAILABLE_YEARS))
        raise BadRequest(f"Unsupported year. Choose from: {supported_years}.")

    limit = _parse_integer_query("limit", 1000)
    offset = _parse_integer_query("offset", 0)
    if not 1 <= limit <= 10000:
        raise BadRequest("Query parameter 'limit' must be between 1 and 10000.")
    if offset < 0:
        raise BadRequest("Query parameter 'offset' cannot be negative.")

    data = load_all_datasets()
    state_name = request.args.get("state", "").strip()
    if state_name:
        if region_type and region_type != "lga":
            raise BadRequest("The 'state' filter is only supported for LGA data.")
        file_prefix = STATE_FILE_PREFIXES.get(state_name)
        if file_prefix is None:
            raise BadRequest("Unsupported state or territory name.")
        data = data.loc[
            (data["region_type"].str.lower() == "lga")
            & data["source_file"].str.startswith(file_prefix)
        ]
    if region_type:
        if region_type == "regional":
            data = data.loc[data["region_type"].str.lower() == "regional"]
        else:
            data = data.loc[data["region_type"].str.lower() == region_type]
    if year_value is not None:
        data = data.loc[data["census_year"] == year]

    search = request.args.get("region_name", "").strip()
    if search:
        data = data.loc[
            data["region_name"].str.contains(search, case=False, na=False, regex=False)
        ]

    total = len(data)
    page = data.iloc[offset : offset + limit]
    records = json.loads(page.to_json(orient="records"))
    return jsonify(
        {
            "data": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
