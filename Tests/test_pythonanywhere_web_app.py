import importlib.util
from pathlib import Path


WEB_APP_PATH = (
    Path(__file__).resolve().parents[1]
    / "Interface (Frontend)"
    / "web_app.py"
)
SPEC = importlib.util.spec_from_file_location("pythonanywhere_web_app", WEB_APP_PATH)
assert SPEC is not None and SPEC.loader is not None
WEB_APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEB_APP)


def test_wsgi_entry_exposes_frontend_and_health_routes():
    client = WEB_APP.application.test_client()

    page_response = client.get("/")
    health_response = client.get("/api/health")

    assert page_response.status_code == 200
    assert b"First Peoples" in page_response.data
    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}
