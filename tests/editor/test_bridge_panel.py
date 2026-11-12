import pytest
from nyx_bridge.client import NyxClient
from PySide6 import QtGui, QtWidgets

from nyx.core import session as session_module
from nyx.core.session import NyxSession
from nyx.editor.widgets.bridge_panel import BridgePanel
from nyx.static.enums import EditorUIObject


@pytest.fixture
def session(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(session_module, "BRIDGE_ADDRESS_FILE_PATH", tmp_path / "b.json")
    session = NyxSession(config=qapp.config)
    monkeypatch.setattr(session.config.values.bridge, "port", 0)
    yield session
    session.shutdown()


@pytest.fixture
def panel(session, qtbot):
    widget = BridgePanel(session)
    qtbot.addWidget(widget)
    return widget


def test_panel_shows_a_stopped_server_before_it_is_started(panel):
    assert panel.status_label.text() == "Stopped"
    assert panel.toggle_button.text() == "Start"
    assert panel.address_label.text() == "-"
    assert not panel.copy_address_button.isEnabled()
    assert not panel.copy_token_button.isEnabled()
    assert panel.clients_table.rowCount() == 0


def test_start_and_stop_button_control_the_server(panel, session):
    panel.toggle_button.click()

    server = session.bridge_server
    assert server.is_running
    assert panel.status_label.text() == "Running"
    assert panel.toggle_button.text() == "Stop"
    assert panel.address_label.text() == f"{server.host}:{server.port}"

    panel.toggle_button.click()

    assert not server.is_running
    assert panel.status_label.text() == "Stopped"
    assert panel.toggle_button.text() == "Start"


def test_token_is_hidden_until_shown(panel, session):
    panel.toggle_button.click()
    token = session.bridge_server.token

    password = QtWidgets.QLineEdit.EchoMode.Password
    assert panel.token_edit.text() == token
    assert panel.token_edit.echoMode() == password
    panel.show_token_button.click()
    assert panel.token_edit.echoMode() == QtWidgets.QLineEdit.EchoMode.Normal
    panel.show_token_button.click()
    assert panel.token_edit.echoMode() == password


def test_copy_buttons_put_address_and_token_on_the_clipboard(panel, session):
    panel.toggle_button.click()
    server = session.bridge_server
    clipboard = QtGui.QGuiApplication.clipboard()

    panel.copy_address_button.click()
    assert clipboard.text() == f"{server.host}:{server.port}"
    panel.copy_token_button.click()
    assert clipboard.text() == server.token


def test_clients_are_listed_while_they_are_connected(panel, session, qtbot):
    server = session.start_bridge_server()

    client = NyxClient(
        name="client-1", address=("127.0.0.1", server.port), token=server.token
    )
    client.connect()
    try:
        qtbot.waitUntil(lambda: panel.clients_table.rowCount() == 1, timeout=5000)
        assert panel.clients_table.item(0, 0).text() == "client-1"
        assert panel.clients_table.item(0, 1).text() == client.CLIENT_KIND

        server.wait_for_client(name="client-1", timeout=5).close()
        qtbot.waitUntil(lambda: panel.clients_table.rowCount() == 0, timeout=5000)
    finally:
        client.stop()


def test_main_window_has_a_bridge_dock(main_window):
    docks = {dock.objectName(): dock for dock in main_window.dock_widgets}

    assert docks[EditorUIObject.BRIDGE_DOCK].widget() is main_window.bridge_panel


def test_the_name_column_takes_the_free_width(panel):
    header = panel.clients_table.horizontalHeader()
    stretch = QtWidgets.QHeaderView.ResizeMode.Stretch

    assert header.sectionResizeMode(0) == stretch
    assert not header.stretchLastSection()
    for column in range(1, panel.clients_table.columnCount()):
        assert header.sectionResizeMode(column) != stretch


def test_the_other_columns_keep_a_reasonable_width_with_no_clients(panel):
    header = panel.clients_table.horizontalHeader()

    for column, width in enumerate(panel.CLIENT_COLUMN_WIDTHS, start=1):
        assert header.sectionSize(column) == width
