"""WSGI entry point for deploying the census app on PythonAnywhere."""

import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "Source (Backend)"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from data_loader import app as application
