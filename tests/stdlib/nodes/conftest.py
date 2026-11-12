import pytest

from nyx.core import session as session_module


@pytest.fixture
def bridge_server(qapp, tmp_path, monkeypatch):
    """Server of the application session, as the bridge nodes find it."""
    session = qapp.session
    monkeypatch.setattr(session_module, "BRIDGE_ADDRESS_FILE_PATH", tmp_path / "b.json")
    monkeypatch.setattr(session, "_bridge_server", None)
    monkeypatch.setattr(session.config.values.bridge, "port", 0)
    running = session.start_bridge_server()
    yield running
    session.shutdown()
