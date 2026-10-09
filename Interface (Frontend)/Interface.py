"""Run the browser-based census map and its backing data API."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "Source (Backend)"
sys.path.insert(0, str(BACKEND_DIR))

from data_loader import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
