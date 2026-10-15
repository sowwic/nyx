import json

from PySide6 import QtCore, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import io


def select(stage_editor, *nodes):
    selection_model = stage_editor.selection_model
    selection_model.clearSelection()
    for node in nodes:
        selection_model.select(
            node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
        )


def root_children(stage_editor):
    stage = stage_editor.stage
    return [n.name for n in stage.list_children(stage.root_node)]


# ---- Tree view ----
def test_tree_view_follows_active_stage(main_window, stage_editor):
    assert main_window.stage_tree_view.stage is stage_editor.stage
    assert main_window.undo_group.activeStack() is stage_editor.stage.undo_stack


def test_tree_view_selected_nodes(main_window, stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    select(stage_editor, a)
    tree = main_window.stage_tree_view
    assert list(tree.selected_nodes()) == [a]
    assert tree.current_node() is a


def test_tree_view_current_node_none_when_nothing_selected(main_window, stage_editor):
    assert main_window.stage_tree_view.current_node() is None


def test_tree_view_delete_selected(main_window, stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    select(stage_editor, a)
    main_window.stage_tree_view.delete_selected_node()
    assert root_children(stage_editor) == ["b"]


def test_tree_view_delete_key(main_window, stage_editor, create_node, qtbot):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    qtbot.keyClick(main_window.stage_tree_view, QtCore.Qt.Key.Key_Delete)
    assert root_children(stage_editor) == []


def test_tree_view_copy_then_paste_duplicates(main_window, stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    tree = main_window.stage_tree_view

    tree.copy_selected_nodes()
    stage_editor.selection_model.clearSelection()
    tree.paste_nodes_from_clipboard()

    assert len(root_children(stage_editor)) == 2


def test_tree_view_cut_removes_nodes_and_paste_restores(
    main_window, stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    tree = main_window.stage_tree_view

    tree.cut_selected_nodes()
    assert root_children(stage_editor) == []
    tree.paste_nodes_from_clipboard()
    assert len(root_children(stage_editor)) == 1


def test_tree_view_paste_with_empty_clipboard_warns(main_window, stage_editor, caplog):
    QtWidgets.QApplication.clipboard().setText("")
    with caplog.at_level("WARNING"):
        main_window.stage_tree_view.paste_nodes_from_clipboard()
    assert "No nodes found in the clipboard" in caplog.text
    assert root_children(stage_editor) == []


def test_tree_view_copy_path(main_window, stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    main_window.stage_tree_view.copy_selected_node_path()
    assert QtWidgets.QApplication.clipboard().text() == a.path.as_posix()


def test_tree_view_double_click_emits_node(
    main_window, stage_editor, create_node, qtbot
):
    a = create_node(stage_editor.stage, "a")
    tree = main_window.stage_tree_view
    with qtbot.waitSignal(tree.node_doubleclicked, timeout=1000) as blocker:
        tree.doubleClicked.emit(a.index())
    assert blocker.args == [a]


# ---- Graph view ----
def test_graph_view_delete_selected(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    select(stage_editor, a)
    assert not stage_editor.gr_stage.is_gr_node_selection_empty()
    stage_editor.gr_view.delete_selected()
    assert root_children(stage_editor) == ["b"]


def test_graph_view_delete_without_selection_warns(stage_editor, create_node, caplog):
    create_node(stage_editor.stage, "a")
    with caplog.at_level("WARNING"):
        stage_editor.gr_view.delete_selected()
    assert root_children(stage_editor) == ["a"]
    assert "No nodes selected" in caplog.text


def test_graph_view_copy_paste_roundtrip(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    view = stage_editor.gr_view
    view.copy_selected_nodes()
    view.paste_nodes_from_clipboard()
    assert len(root_children(stage_editor)) == 2


def test_graph_scene_mirrors_stage_nodes(stage_editor, create_node):
    create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    assert len(list(stage_editor.gr_stage.gr_nodes())) == 2


def test_selection_enables_selection_actions(stage_editor, create_node, give_focus):
    a = create_node(stage_editor.stage, "a")
    give_focus(stage_editor.gr_view)
    copy_action = ACTION_REGISTRY.action(ActionId.COPY)
    ACTION_ROUTER.refresh_enabled()
    assert not copy_action.isEnabled()

    select(stage_editor, a)
    ACTION_ROUTER.refresh_enabled()
    assert copy_action.isEnabled()


def test_copy_action_dispatches_to_focused_view(
    main_window, stage_editor, create_node, give_focus
):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    give_focus(main_window.stage_tree_view)
    QtWidgets.QApplication.clipboard().setText("")

    ACTION_REGISTRY.action(ActionId.COPY).trigger()

    data = json.loads(QtWidgets.QApplication.clipboard().text())
    assert [n["name"] for n in data["nyx_nodes"]] == ["a"]


# ---- io ----
def test_export_single_node(
    main_window, stage_editor, create_node, tmp_path, monkeypatch
):
    a = create_node(stage_editor.stage, "exported")
    select(stage_editor, a)
    target = tmp_path / "node.nyx"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )
    io.export_selected_nodes()
    assert json.loads(target.read_text())["name"] == "exported"


def test_export_without_selection_is_noop(main_window, stage_editor, monkeypatch):
    called = []
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: called.append(1)
    )
    io.export_selected_nodes()
    assert called == []


def test_export_multiple_nodes_into_directory(
    main_window, stage_editor, create_node, tmp_path, monkeypatch
):
    a = create_node(stage_editor.stage, "first")
    b = create_node(stage_editor.stage, "second")
    select(stage_editor, a, b)
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path)
    )
    io.export_selected_nodes()
    assert {p.name for p in tmp_path.glob("*.nyx")} == {"first.nyx", "second.nyx"}


def test_import_nodes_from_file(
    main_window, stage_editor, create_node, tmp_path, monkeypatch
):
    source = create_node(stage_editor.stage, "imported")
    file_path = tmp_path / "imported.nyx"
    source.export_to_json(file_path)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileNames",
        lambda *a, **k: ([str(file_path)], ""),
    )

    io.import_nodes_from_explorer()

    assert len(root_children(stage_editor)) == 2


def test_import_cancelled_does_nothing(main_window, stage_editor, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileNames", lambda *a, **k: ([], "")
    )
    io.import_nodes_from_explorer()
    assert root_children(stage_editor) == []


def test_import_without_stage_graph_does_nothing(main_window, monkeypatch):
    called = []
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileNames", lambda *a, **k: called.append(1)
    )
    io.import_nodes_from_explorer()
    assert called == []


def test_reference_into_itself_is_rejected(
    main_window, stage_editor, create_node, tmp_path, caplog
):
    stage = stage_editor.stage
    create_node(stage, "x")
    file_path = tmp_path / "self.nyx"
    stage.export_json(file_path)
    stage.file_path = file_path

    with caplog.at_level("ERROR"):
        io._import_nodes(stage_editor, [file_path], as_reference=True)
    assert "Can't reference file into itself" in caplog.text
