import copy

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
    # Fixed size: the default depends on the saved config / screen, which makes
    # geometry-dependent tests behave differently locally and on CI.
    window.resize(1200, 900)
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


@pytest.fixture
def restore_config():
    """Return a function that remembers config values and puts them back after the test.

    The config outlives a test, so a value a test sets must not leak into the next one.
    """
    saved = []

    def remember(values, *names):
        saved.append(
            (values, {name: copy.deepcopy(getattr(values, name)) for name in names})
        )
        return values

    yield remember
    for values, old in reversed(saved):
        for name, value in old.items():
            setattr(values, name, value)


@pytest.fixture
def stage_config(main_window, restore_config):
    """Graphics stage values of the live config, restored after the test."""
    return restore_config(
        main_window.config.values.editor_widgets.graphics_stage,
        "highlight_flow_chain",
        "highlight_flow_chain_style",
        "link_style",
        "viewport_debug_overlay",
        "background_style",
        "background_color",
    )


@pytest.fixture
def animation_config(main_window, restore_config):
    """Animation values of the live config, restored after the test."""
    return restore_config(
        main_window.config.values.editor_style.animations, "link_pulse", "link_glow"
    )


@pytest.fixture
def chain_link(stage_editor, create_node):
    """The graphics link from a flow start to an action, as the chain highlight has it.

    Returns:
        tuple: the stage editor and the link. The link pulses, it is on the chain.
    """
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )
    return stage_editor, stage_editor.gr_stage.gr_links()[0]
