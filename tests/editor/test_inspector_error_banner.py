import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes
from nyx.static.enums import NodeExecutionStatus


@pytest.fixture
def failing_node(main_window, stage_editor, create_node):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.EMPTY)
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    main_window.inspector.update_data()
    return node


def fail(node, error):
    node.raised_exception = error
    node.execution_status = NodeExecutionStatus.ERROR


def test_no_banner_for_a_node_that_did_not_fail(main_window, failing_node):
    assert main_window.inspector._error_banner.isHidden()


def test_banner_shows_the_error_when_the_node_fails(main_window, failing_node):
    banner = main_window.inspector._error_banner

    fail(failing_node, ValueError("it broke"))

    assert not banner.isHidden()
    assert banner.summary == "ValueError: it broke"


def test_banner_hides_again_when_the_node_is_reset(main_window, failing_node):
    banner = main_window.inspector._error_banner
    fail(failing_node, ValueError("x"))

    failing_node.reset_execution_status()

    assert banner.isHidden()
    assert failing_node.raised_exception is None


def test_long_messages_stay_on_one_line_and_open_in_full(
    main_window, failing_node, monkeypatch
):
    banner = main_window.inspector._error_banner
    message = "line one\n" + "very long " * 50
    fail(failing_node, RuntimeError(message))

    assert "\n" not in banner._label.text()
    assert banner._label.toolTip() == banner.summary

    shown = []
    from nyx.editor.widgets import inspector_error_banner as module

    monkeypatch.setattr(
        module.ErrorDetailsDialog,
        "exec",
        lambda self: shown.append(self.text_edit.toPlainText()),
    )
    banner.show_details()

    assert "RuntimeError" in shown[0] and message.rstrip() in shown[0]


def test_banner_follows_the_selection(
    main_window, stage_editor, failing_node, create_node
):
    banner = main_window.inspector._error_banner
    fail(failing_node, ValueError("x"))
    other = create_node(stage_editor.stage, "b", type_id=CoreNodes.EMPTY)
    stage_editor.selection_model.clear()
    stage_editor.selection_model.select(
        other.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )

    main_window.inspector.update_data()

    assert banner.isHidden()
