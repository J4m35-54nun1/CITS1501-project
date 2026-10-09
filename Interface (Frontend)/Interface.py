"""Run the browser-based census map and its backing data API."""

import sys
from pathlib import Path

from werkzeug.serving import make_server

BACKEND_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)"
sys.path.insert(0, str(BACKEND_DIR))

from data_loader import app


def run_server() -> None:
    """Serve the app without a reloader child and close the socket on exit."""
    server = make_server("127.0.0.1", 5000, app, threaded=True)
    print("Census Explorer running at http://127.0.0.1:5000 (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCensus Explorer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
