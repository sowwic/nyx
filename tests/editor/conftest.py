import pytest
from PySide6 import QtCore, QtWidgets

from nyx.api.v1 import CoreNodes, commands


def close_all_stage_windows(main_window) -> None:
    for sub_window in main_window.mdi_area.subWindowList():
        sub_window.widget().maybe_save = lambda: True  # avoid modal save prompt
        sub_window.close()
    QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


@pytest.fixture
def main_window(qapp, qtbot):
    """The application's editor main window, with no stage windows open."""
    window = qapp.main_window()
    close_all_stage_windows(window)
    yield window
    close_all_stage_windows(window)


@pytest.fixture
def stage_editor(main_window, qtbot):
    """A fresh, active `StageGraphEditor` inside the main window."""
    main_window.on_stage_new()
    qtbot.waitUntil(lambda: main_window.current_stage_graph is not None, timeout=2000)
    return main_window.current_stage_graph


@pytest.fixture
def create_node():
    """Factory pushing a `CreateNodeCommand` and returning the new node."""

    def _create(stage, name="node", parent=None, type_id=CoreNodes.EMPTY):
        command = commands.CreateNodeCommand(
            stage=stage, type_id=type_id, name=name, parent_node=parent
        )
        stage.push_command(command)
        return command.result_node

    return _create


@pytest.fixture
def give_focus(qtbot):
    """Return a helper that activates the widget's window and focuses it."""

    def _give_focus(widget: QtWidgets.QWidget) -> None:
        window = widget.window()
        if not window.isVisible():
            window.show()
            qtbot.waitExposed(window)
        window.activateWindow()
        widget.setFocus()
        qtbot.waitUntil(widget.hasFocus, timeout=2000)

    return _give_focus
