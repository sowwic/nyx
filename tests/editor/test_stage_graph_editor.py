import pathlib
from unittest import mock

import pytest
from PySide6 import QtWidgets

from nyx.static.vars import ROOT_NODE_PATH


def test_new_editor_starts_at_root_scope(stage_editor):
    assert stage_editor.get_scope_path() == ROOT_NODE_PATH
    # A stage without a file path always counts as modified.
    assert stage_editor.windowTitle() == f"{stage_editor.DEFAULT_TITLE}*"


def test_set_scope_emits_signal(stage_editor, create_node, qtbot):
    node = create_node(stage_editor.stage, "parent")
    with qtbot.waitSignal(stage_editor.scope_changed) as blocker:
        stage_editor.set_scope_path(node)
    assert blocker.args == [node.path]
    assert stage_editor.get_scope_path() == node.path


def test_set_scope_silent_does_not_emit(stage_editor, create_node, qtbot):
    node = create_node(stage_editor.stage, "parent")
    with qtbot.assertNotEmitted(stage_editor.scope_changed):
        stage_editor.set_scope_path(node, silent=True)
    assert stage_editor.get_scope_path() == node.path


def test_invalid_scope_falls_back_to_nearest_existing_parent(stage_editor, create_node):
    parent = create_node(stage_editor.stage, "parent")
    stage_editor.set_scope_path(parent.path / "missing" / "deeper")
    assert stage_editor.get_scope_path() == parent.path


def test_scope_back_and_root(stage_editor, create_node):
    parent = create_node(stage_editor.stage, "parent")
    child = create_node(stage_editor.stage, "child", parent=parent)
    stage_editor.set_scope_path(child)

    stage_editor.scope_back()
    assert stage_editor.get_scope_path() == parent.path
    stage_editor.set_scope_path(child)
    stage_editor.scope_root()
    assert stage_editor.get_scope_path() == ROOT_NODE_PATH


def test_scope_back_at_root_is_noop(stage_editor, qtbot):
    with qtbot.assertNotEmitted(stage_editor.scope_changed):
        stage_editor.scope_back()


def test_deleting_scope_node_moves_scope_to_parent(stage_editor, create_node):
    from nyx.api.v1 import commands

    parent = create_node(stage_editor.stage, "parent")
    child = create_node(stage_editor.stage, "child", parent=parent)
    stage_editor.set_scope_path(child)

    stage_editor.stage.push_command(
        commands.DeleteNodeCommand(stage_editor.stage, [child])
    )
    assert stage_editor.get_scope_path() == parent.path


def test_filter_nodes_by_scope(stage_editor, create_node):
    top = create_node(stage_editor.stage, "top")
    nested = create_node(stage_editor.stage, "nested", parent=top)
    assert stage_editor.filter_nodes_by_scope([top, nested]) == [top]
    stage_editor.set_scope_path(top)
    assert stage_editor.filter_nodes_by_scope([top, nested]) == [nested]


def test_title_uses_file_name_once_saved(stage_editor, tmp_path):
    target = tmp_path / "named.nyx"
    stage_editor.stage.export_json(target)
    stage_editor.update_title()
    assert stage_editor.windowTitle() == "named.nyx"


def test_maybe_save_true_for_new_empty_stage(stage_editor):
    assert stage_editor.maybe_save() is True


@pytest.mark.parametrize(
    ("button", "expected"),
    [
        (QtWidgets.QMessageBox.Discard, True),
        (QtWidgets.QMessageBox.Cancel, False),
    ],
)
def test_maybe_save_respects_prompt_choice(
    stage_editor, create_node, monkeypatch, button, expected
):
    create_node(stage_editor.stage)
    warning = mock.Mock(return_value=button)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", warning)
    assert stage_editor.maybe_save() is expected
    warning.assert_called_once()


def test_save_as_writes_file_and_updates_title(
    stage_editor, create_node, tmp_path: pathlib.Path, monkeypatch
):
    create_node(stage_editor.stage, "saved_node")
    target = tmp_path / "stage.nyx"
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        mock.Mock(return_value=(str(target), "")),
    )
    assert stage_editor.on_stage_save_as() is True
    assert target.is_file()
    assert "saved_node" in target.read_text()


def test_save_as_cancelled_writes_nothing(stage_editor, tmp_path, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", mock.Mock(return_value=("", ""))
    )
    assert stage_editor.on_stage_save_as() is False


def test_from_json_file_roundtrip(
    main_window, stage_editor, create_node, tmp_path, monkeypatch, qtbot
):
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

    create_node(stage_editor.stage, "persisted")
    target = tmp_path / "stage.nyx"
    stage_editor.stage.export_json(target)

    loaded = StageGraphEditor.from_json_file(target)
    qtbot.addWidget(loaded)
    names = [n.name for n in loaded.stage.list_children(loaded.stage.root_node)]
    assert names == ["persisted"]
    assert loaded.windowTitle() == "stage.nyx"


def test_scope_widget_follows_editor_scope(stage_editor, create_node):
    node = create_node(stage_editor.stage, "parent")
    scope_widget = stage_editor.graph_scope_widget
    assert scope_widget.path_line_edit.text() == ROOT_NODE_PATH.as_posix()

    stage_editor.set_scope_path(node)
    assert scope_widget.path_line_edit.text() == node.path.as_posix()


def test_scope_widget_return_pressed_sets_scope(stage_editor, create_node, qtbot):
    from PySide6 import QtCore

    node = create_node(stage_editor.stage, "target")
    scope_widget = stage_editor.graph_scope_widget
    scope_widget.path_line_edit.setText(node.path.as_posix())
    qtbot.keyClick(scope_widget.path_line_edit, QtCore.Qt.Key.Key_Return)
    assert stage_editor.get_scope_path() == node.path


def test_scope_widget_buttons(stage_editor, create_node, qtbot):
    parent = create_node(stage_editor.stage, "parent")
    child = create_node(stage_editor.stage, "child", parent=parent)
    stage_editor.set_scope_path(child)
    scope_widget = stage_editor.graph_scope_widget

    from PySide6 import QtCore

    qtbot.mouseClick(scope_widget.scope_back_btn, QtCore.Qt.MouseButton.LeftButton)
    assert stage_editor.get_scope_path() == parent.path
    qtbot.mouseClick(scope_widget.scope_root_btn, QtCore.Qt.MouseButton.LeftButton)
    assert stage_editor.get_scope_path() == ROOT_NODE_PATH


def test_show_nodes_palette_centered_dims_window_and_shows_palette(
    stage_editor, monkeypatch
):
    from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

    popup = mock.Mock()
    monkeypatch.setattr(PopupNodesPalette, "popup_centered", popup)
    stage_editor.show_nodes_palette_centered()
    popup.assert_called_once_with(None)
