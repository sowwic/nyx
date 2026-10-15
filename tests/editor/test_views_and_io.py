import json

import pytest

from PySide6 import QtCore, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
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
    assert not copy_action.isEnabled()

    select(stage_editor, a)  # no manual refresh: the selection drives it
    assert copy_action.isEnabled()

    stage_editor.selection_model.clearSelection()
    assert not copy_action.isEnabled()


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


def place(stage_editor, *positions_by_node):
    """Move nodes in the model and rebuild so their graphics items follow."""
    for node, (x, y) in positions_by_node:
        node.set_position(QtCore.QPointF(x, y))
    stage_editor.gr_stage.rebuild_current_scope()


def _visible_scene_rect(view):
    return view.mapToScene(view.viewport().rect()).boundingRect()


def test_graph_view_focus_centers_on_selected_nodes(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    place(stage_editor, (a, (0, 0)), (b, (2000, 1000)))
    select(stage_editor, a, b)
    view = stage_editor.gr_view

    view.focus_on_selected_nodes()

    united = a.gr_node.sceneBoundingRect().united(b.gr_node.sceneBoundingRect())
    center = view.get_center_position()
    # Tolerance: a few viewport pixels at the reduced zoom.
    assert center.x() == pytest.approx(united.center().x(), abs=10)
    assert center.y() == pytest.approx(united.center().y(), abs=10)


def test_graph_view_focus_zooms_out_to_fit_distant_nodes(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    place(stage_editor, (a, (-5000, -3000)), (b, (5000, 3000)))
    select(stage_editor, a, b)
    view = stage_editor.gr_view
    zoom_before = view.zoom

    view.focus_on_selected_nodes()

    assert view.zoom < zoom_before
    assert view.zoom >= view.zoom_range[0]
    visible = _visible_scene_rect(view)
    for node in (a, b):
        assert visible.contains(node.gr_node.sceneBoundingRect())


def test_graph_view_focus_does_not_magnify_beyond_max_zoom(stage_editor, create_node):
    node = create_node(stage_editor.stage, "tiny")
    select(stage_editor, node)
    view = stage_editor.gr_view

    view.focus_on_selected_nodes()

    assert view.zoom == view.zoom_range[1]
    assert view.transform().m11() == pytest.approx(1.0)


def test_graph_view_focus_keeps_zoom_counter_consistent_with_scale(
    stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    place(stage_editor, (a, (-4000, 0)), (b, (4000, 0)))
    select(stage_editor, a, b)
    view = stage_editor.gr_view

    view.focus_on_selected_nodes()

    expected = view.zoom_in_factor ** (view.zoom - view.DEFAULT_ZOOM)
    assert view.transform().m11() == pytest.approx(expected)


def test_graph_view_focus_without_selection_is_noop(stage_editor, create_node):
    create_node(stage_editor.stage, "a")
    stage_editor.gr_view.focus_on_selected_nodes()  # must not raise


def test_tree_view_focus_selected_delegates_to_graph_view(
    main_window, stage_editor, create_node, monkeypatch
):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    calls = []
    monkeypatch.setattr(
        stage_editor.gr_view, "focus_on_selected_nodes", lambda: calls.append(1)
    )
    main_window.stage_tree_view.focus_on_selected_nodes()
    assert calls == [1]


def test_focus_action_from_tree_view_centers_graph(
    main_window, stage_editor, create_node, give_focus
):
    node = create_node(stage_editor.stage, "far")
    place(stage_editor, (node, (500, 400)))
    select(stage_editor, node)
    give_focus(main_window.stage_tree_view)
    action = ACTION_REGISTRY.action(ActionId.FOCUS_SELECTED)
    assert action.isEnabled()

    action.trigger()

    united = node.gr_node.sceneBoundingRect()
    center = stage_editor.gr_view.get_center_position()
    assert center.x() == pytest.approx(united.center().x(), abs=2)
    assert center.y() == pytest.approx(united.center().y(), abs=2)


def test_focus_action_disabled_in_tree_without_selection(
    main_window, stage_editor, give_focus
):
    give_focus(main_window.stage_tree_view)
    assert not ACTION_REGISTRY.action(ActionId.FOCUS_SELECTED).isEnabled()


def test_tree_selection_after_focus_enables_focus_action(
    main_window, stage_editor, create_node, give_focus
):
    """Click order: the tree gets focus first, then the selection changes."""
    node = create_node(stage_editor.stage, "n")
    tree = main_window.stage_tree_view
    give_focus(tree)
    action = ACTION_REGISTRY.action(ActionId.FOCUS_SELECTED)
    assert not action.isEnabled()

    tree.selectionModel().select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
    )

    assert action.isEnabled()
    assert ACTION_REGISTRY.action(ActionId.DELETE_NODE).isEnabled()


# ---- Context menus ----
def menu_layout(menu):
    """Action ids (or "-" for separators) in menu order."""
    return [
        "-" if action.isSeparator() else action.objectName() for action in menu.actions()
    ]


NO_SELECTION_LAYOUT = [ActionId.CREATE_NODE, ActionId.PASTE]
WITH_SELECTION_LAYOUT = [
    ActionId.CREATE_NODE,
    "-",
    ActionId.COPY,
    ActionId.CUT,
    ActionId.PASTE,
    "-",
    ActionId.FOCUS_SELECTED,
    ActionId.COPY_NODE_PATH,
    ActionId.DELETE_NODE,
]


@pytest.mark.parametrize(
    ("has_selection", "expected"),
    [(False, NO_SELECTION_LAYOUT), (True, WITH_SELECTION_LAYOUT)],
)
def test_shared_nodes_context_menu_layout(qtbot, has_selection, expected):
    from nyx.editor.utils.context_menus import build_nodes_context_menu

    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    menu = build_nodes_context_menu(parent, has_selection)
    assert menu_layout(menu) == expected


@pytest.mark.parametrize("with_selection", [False, True])
def test_graph_and_tree_context_menus_match(
    main_window, stage_editor, create_node, monkeypatch, with_selection
):
    node = create_node(stage_editor.stage, "n")
    if with_selection:
        select(stage_editor, node)
    layouts = {}

    def capture(name):
        def fake_exec(self, *args, **kwargs):
            layouts[name] = menu_layout(self)

        return fake_exec

    monkeypatch.setattr(QtWidgets.QMenu, "exec_", capture("graph"))
    stage_editor.gr_view.show_context_menu(QtCore.QPoint(5, 5))
    monkeypatch.setattr(QtWidgets.QMenu, "exec_", capture("tree"))
    main_window.stage_tree_view.show_context_menu(QtCore.QPoint(5, 5))

    assert layouts["graph"] == layouts["tree"]
    expected = WITH_SELECTION_LAYOUT if with_selection else NO_SELECTION_LAYOUT
    assert layouts["graph"] == expected


def test_graph_view_copy_node_path(stage_editor, create_node):
    node = create_node(stage_editor.stage, "pathy")
    select(stage_editor, node)
    stage_editor.gr_view.copy_selected_node_path()
    assert QtWidgets.QApplication.clipboard().text() == node.path.as_posix()


def test_graph_view_copy_node_path_without_selection_keeps_clipboard(stage_editor):
    QtWidgets.QApplication.clipboard().setText("untouched")
    stage_editor.gr_view.copy_selected_node_path()
    assert QtWidgets.QApplication.clipboard().text() == "untouched"


def test_graph_view_menu_actions_work_when_focused(
    stage_editor, create_node, give_focus
):
    node = create_node(stage_editor.stage, "victim")
    select(stage_editor, node)
    give_focus(stage_editor.gr_view)

    copy_path = ACTION_REGISTRY.action(ActionId.COPY_NODE_PATH)
    delete_node = ACTION_REGISTRY.action(ActionId.DELETE_NODE)
    assert copy_path.isEnabled() and delete_node.isEnabled()

    copy_path.trigger()
    assert QtWidgets.QApplication.clipboard().text() == node.path.as_posix()
    delete_node.trigger()
    assert root_children(stage_editor) == []


def test_graph_view_delete_node_disabled_without_selection(stage_editor, give_focus):
    give_focus(stage_editor.gr_view)
    assert not ACTION_REGISTRY.action(ActionId.DELETE_NODE).isEnabled()
    assert not ACTION_REGISTRY.action(ActionId.COPY_NODE_PATH).isEnabled()


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
