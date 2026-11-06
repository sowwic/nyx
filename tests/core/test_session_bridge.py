import logging

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


def test_there_is_no_server_before_it_is_started(session):
    assert session.bridge_server is None


def test_server_listens_and_writes_the_address_file_clients_read(session, address_file):
    server = session.start_bridge_server()

    assert server is session.bridge_server
    assert server.name == BRIDGE_SERVER_NAME
    assert server.is_running
    found = protocol.read_address_file(address_file)
    assert (found.port, found.token) == (server.port, server.token)


def test_address_and_port_are_logged_without_the_token(session, caplog):
    with caplog.at_level(logging.INFO, logger=session_module.LOGGER.name):
        server = session.start_bridge_server()

    messages = [record.getMessage() for record in caplog.records]
    assert any(f"{server.host}:{server.port}" in message for message in messages)
    assert not any(server.token in message for message in messages)


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


def test_disabled_server_is_not_started(session, address_file, monkeypatch):
    monkeypatch.setattr(session.config.values.bridge, "enabled", False)

    assert session.autostart_bridge_server() is None
    assert session.bridge_server is None
    assert not address_file.exists()
    assert session.start_bridge_server().is_running


def test_unavailable_port_is_logged_and_not_raised(session, monkeypatch):
    def fail(self):
        raise OSError("port in use")

    monkeypatch.setattr(session_module.BridgeServer, "start", fail)

    assert session.start_bridge_server() is None


def test_server_is_stopped_when_the_application_quits(qapp, monkeypatch, address_file):
    monkeypatch.setattr(qapp.session, "_bridge_server", None)
    monkeypatch.setattr(qapp.session.config.values.bridge, "port", 0)
    server = qapp.session.start_bridge_server()

    qapp.aboutToQuit.emit()

    assert not server.is_running
