import pytest
from nyx_bridge import protocol

from nyx.core import session as session_module
from nyx.core.session import BRIDGE_SERVER_NAME, NyxSession


@pytest.fixture
def address_file(tmp_path, monkeypatch):
    path = tmp_path / "bridge.json"
    monkeypatch.setattr(session_module, "BRIDGE_ADDRESS_FILE_PATH", path)
    return path


@pytest.fixture
def session(qapp, address_file, monkeypatch):
    session = NyxSession(config=qapp.config)
    values = session.config.values.bridge
    for name, value in (("enabled", True), ("port", 0), ("token", "")):
        monkeypatch.setattr(values, name, value)
    yield session
    session.shutdown()


def test_server_listens_and_writes_the_address_file_clients_read(session, address_file):
    server = session.start_bridge_server()

    assert server is session.bridge_servers.get_server(BRIDGE_SERVER_NAME)
    assert server.is_running
    found = protocol.read_address_file(address_file)
    assert (found.port, found.token) == (server.port, server.token)


def test_address_file_is_removed_on_shutdown(session, address_file):
    session.start_bridge_server()

    session.shutdown()

    assert not address_file.exists()


def test_configured_token_is_used(session, monkeypatch):
    monkeypatch.setattr(session.config.values.bridge, "token", "from-config")

    assert session.start_bridge_server().token == "from-config"


def test_starting_twice_keeps_one_server(session):
    first = session.start_bridge_server()

    assert session.start_bridge_server() is first
    assert len(session.bridge_servers.servers) == 1


def test_disabled_server_is_not_started(session, address_file, monkeypatch):
    monkeypatch.setattr(session.config.values.bridge, "enabled", False)

    assert session.start_bridge_server() is None
    assert session.bridge_servers.servers == []
    assert not address_file.exists()


def test_unavailable_port_is_logged_and_not_raised(session, monkeypatch):
    def fail(self):
        raise OSError("port in use")

    monkeypatch.setattr(session_module.BridgeServer, "start", fail)

    assert session.start_bridge_server() is None
