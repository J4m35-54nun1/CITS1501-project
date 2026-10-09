import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


INTERFACE_PATH = (
    Path(__file__).resolve().parents[1] / "Interface (Frontend)" / "Interface.py"
)
SPEC = importlib.util.spec_from_file_location("census_interface", INTERFACE_PATH)
assert SPEC is not None and SPEC.loader is not None
INTERFACE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INTERFACE)


def test_server_closes_when_interrupted():
    server = Mock()
    server.serve_forever.side_effect = KeyboardInterrupt

    with patch.object(INTERFACE, "make_server", return_value=server) as make_server:
        INTERFACE.run_server()

    make_server.assert_called_once_with(
        "127.0.0.1", 5000, INTERFACE.app, threaded=True
    )
    server.server_close.assert_called_once_with()
