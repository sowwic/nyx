import json

import pytest

from PySide6 import QtCore, QtWidgets

from nyx.api.v1 import CoreNodeComponents, CoreNodes, Stage, commands
from nyx.editor.graphics.graphics_cutline import GraphCutLine
from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import context_menus, io


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
    stage_editor.gr_view.edit_actions.delete_selected()
    assert root_children(stage_editor) == ["b"]


def test_graph_view_delete_without_selection_warns(stage_editor, create_node, caplog):
    create_node(stage_editor.stage, "a")
    with caplog.at_level("WARNING"):
        stage_editor.gr_view.edit_actions.delete_selected()
    assert root_children(stage_editor) == ["a"]
    assert "Nothing selected" in caplog.text


def test_graph_view_copy_paste_roundtrip(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    view = stage_editor.gr_view
    view.edit_actions.copy_selected_nodes()
    view.edit_actions.paste_nodes_from_clipboard()
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

    view.edit_actions.focus_on_selected_nodes()

    united = (
        stage_editor.gr_stage.get_gr_node(a)
        .sceneBoundingRect()
        .united(stage_editor.gr_stage.get_gr_node(b).sceneBoundingRect())
    )
    center = view.get_center_position()
    # Tolerance: a couple of viewport pixels, expressed in scene units.
    tolerance = 2 / view.transform().m11()
    assert center.x() == pytest.approx(united.center().x(), abs=tolerance)
    assert center.y() == pytest.approx(united.center().y(), abs=tolerance)


def test_graph_view_focus_zooms_out_to_fit_distant_nodes(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    place(stage_editor, (a, (-1500, -900)), (b, (1500, 900)))
    select(stage_editor, a, b)
    view = stage_editor.gr_view
    zoom_before = view.zoom

    view.edit_actions.focus_on_selected_nodes()

    assert view.zoom < zoom_before
    assert view.zoom >= view.zoom_range[0]
    visible = _visible_scene_rect(view)
    for node in (a, b):
        assert visible.contains(
            stage_editor.gr_stage.get_gr_node(node).sceneBoundingRect()
        )


def test_graph_view_focus_does_not_magnify_beyond_max_zoom(stage_editor, create_node):
    node = create_node(stage_editor.stage, "tiny")
    select(stage_editor, node)
    view = stage_editor.gr_view

    view.edit_actions.focus_on_selected_nodes()

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

    view.edit_actions.focus_on_selected_nodes()

    expected = view.zoom_in_factor ** (view.zoom - view.DEFAULT_ZOOM)
    assert view.transform().m11() == pytest.approx(expected)


def test_graph_view_focus_without_selection_is_noop(stage_editor, create_node):
    create_node(stage_editor.stage, "a")
    stage_editor.gr_view.edit_actions.focus_on_selected_nodes()  # must not raise


def test_tree_view_focus_selected_delegates_to_graph_view(
    main_window, stage_editor, create_node, monkeypatch
):
    a = create_node(stage_editor.stage, "a")
    select(stage_editor, a)
    calls = []
    monkeypatch.setattr(
        stage_editor.gr_view.edit_actions,
        "focus_on_selected_nodes",
        lambda: calls.append(1),
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

    united = stage_editor.gr_stage.get_gr_node(node).sceneBoundingRect()
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
        def fake_show(menu, global_pos):
            layouts[name] = menu_layout(menu)

        return fake_show

    monkeypatch.setattr(context_menus, "show_menu", capture("graph"))
    stage_editor.gr_view.show_context_menu(QtCore.QPoint(5, 5))
    monkeypatch.setattr(context_menus, "show_menu", capture("tree"))
    main_window.stage_tree_view.show_context_menu(QtCore.QPoint(5, 5))

    # Only the graph can show notes and groups, so only it offers creating them.
    graph_layout = [
        action_id
        for action_id in layouts["graph"]
        if action_id not in (ActionId.CREATE_NOTE, ActionId.CREATE_GROUP)
    ]
    assert graph_layout == layouts["tree"]
    assert ActionId.CREATE_NOTE in layouts["graph"]
    assert ActionId.CREATE_GROUP in layouts["graph"]
    expected = WITH_SELECTION_LAYOUT if with_selection else NO_SELECTION_LAYOUT
    assert layouts["tree"] == expected


def test_graph_view_copy_node_path(stage_editor, create_node):
    node = create_node(stage_editor.stage, "pathy")
    select(stage_editor, node)
    stage_editor.gr_view.edit_actions.copy_selected_node_path()
    assert QtWidgets.QApplication.clipboard().text() == node.path.as_posix()


def test_graph_view_copy_node_path_without_selection_keeps_clipboard(stage_editor):
    QtWidgets.QApplication.clipboard().setText("untouched")
    stage_editor.gr_view.edit_actions.copy_selected_node_path()
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
def test_import_stage_from_file(
    main_window, stage_editor, create_node, tmp_path, monkeypatch
):
    source = Stage()
    create_node(source, "imported")
    file_path = tmp_path / "imported.nyx"
    source.export_json(file_path)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileNames",
        lambda *a, **k: ([str(file_path)], ""),
    )

    io.import_stages_from_explorer()

    assert len(root_children(stage_editor)) == 1
    imported_stage = stage_editor.stage.root_node.list_children()[0]
    assert imported_stage.find_child_by_name("imported") is not None


def test_import_cancelled_does_nothing(main_window, stage_editor, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileNames", lambda *a, **k: ([], "")
    )
    io.import_stages_from_explorer()
    assert root_children(stage_editor) == []


def test_import_without_stage_graph_does_nothing(main_window, monkeypatch):
    called = []
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileNames", lambda *a, **k: called.append(1)
    )
    io.import_stages_from_explorer()
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
        io._import_stages(stage_editor, [file_path], as_reference=True)
    assert "Can't reference file into itself" in caplog.text


def test_reference_nodes_creates_a_reference_node(stage_editor, tmp_path):
    stage = stage_editor.stage
    source = tmp_path / "source.nyx"
    other = Stage()
    other.export_json(source)
    stage.export_json(tmp_path / "main.nyx")

    io._import_stages(stage_editor, [source], as_reference=True)

    node = stage.root_node.find_child_by_name("source")
    assert node.get_type_id() == CoreNodes.REFERENCE
    assert node.source == "source.nyx"
    assert node.load_error == ""


def test_nodes_of_a_reference_cant_be_linked(stage_editor, tmp_path):
    from nyx.editor.graphics.graphics_stage import GraphicsStage

    stage = stage_editor.stage
    source = tmp_path / "source.nyx"
    other = Stage()
    other.push_command(
        commands.CreateNodeCommand(stage=other, type_id=CoreNodes.VALUE, name="inner")
    )
    other.export_json(source)
    stage.export_json(tmp_path / "main.nyx")
    io._import_stages(stage_editor, [source], as_reference=True)
    reference = stage.root_node.find_child_by_name("source")
    child = reference.find_child_by_name("inner")

    assert not GraphicsStage.can_link(child["value"], reference["source"])
    assert not GraphicsStage.can_link(reference["source"], child["value"])


# ---- Graphics stage ----
def _gr_names(stage_editor):
    return sorted(g.node.name for g in stage_editor.gr_stage.gr_nodes())


def test_graphics_stage_draws_only_scope_children(stage_editor, create_node):
    stage = stage_editor.stage
    parent = create_node(stage, "parent")
    child = create_node(stage, "child", parent=parent)
    create_node(stage, "grandchild", parent=child)
    create_node(stage, "sibling")
    gr_stage = stage_editor.gr_stage

    assert _gr_names(stage_editor) == ["parent", "sibling"]
    assert gr_stage.get_gr_node(child) is None

    stage_editor.set_scope_path(parent)
    assert _gr_names(stage_editor) == ["child"]

    stage_editor.set_scope_path(child)
    assert _gr_names(stage_editor) == ["grandchild"]


def test_graphics_stage_add_node_rejects_out_of_scope(stage_editor, create_node):
    stage = stage_editor.stage
    parent = create_node(stage, "parent")
    child = create_node(stage, "child", parent=parent)
    assert stage_editor.gr_stage.add_node(child) is None
    assert stage_editor.gr_stage.get_gr_node(child) is None


def test_graphics_stage_rebuild_keeps_items_of_unchanged_nodes(
    stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a")
    gr_a = stage_editor.gr_stage.get_gr_node(a)
    create_node(stage_editor.stage, "b")
    assert stage_editor.gr_stage.get_gr_node(a) is gr_a
    assert _gr_names(stage_editor) == ["a", "b"]


def test_graphics_stage_removes_items_of_deleted_nodes(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    select(stage_editor, a)
    stage_editor.gr_view.edit_actions.delete_selected()
    assert _gr_names(stage_editor) == ["b"]
    stage_editor.stage.undo_stack.undo()
    assert _gr_names(stage_editor) == ["a", "b"]


def test_graphics_node_follows_position_and_undo(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    gr_a = stage_editor.gr_stage.get_gr_node(a)
    command = commands.MoveNodeCommand(
        stage=stage_editor.stage, nodes=[a], new_positions=[QtCore.QPointF(50, 60)]
    )
    stage_editor.stage.push_command(command)
    assert gr_a.pos() == QtCore.QPointF(50, 60)
    stage_editor.stage.undo_stack.undo()
    assert gr_a.pos() == QtCore.QPointF(0, 0)


def test_graphics_node_title_follows_rename_and_grows(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    gr_a = stage_editor.gr_stage.get_gr_node(a)
    assert gr_a.width == gr_a.options.min_width
    stage_editor.stage.push_command(
        commands.RenameNodeCommand(
            stage=stage_editor.stage, node=a, new_name="a_very_long_node_name_indeed"
        )
    )
    assert gr_a.title_item.toPlainText() == "a_very_long_node_name_indeed"
    assert gr_a.width > gr_a.options.min_width


def test_graphics_node_creates_plugs_for_linkable_components(stage_editor, create_node):
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    plug_count = len(gr_node.plugs)

    add_cmd = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name="test_cpnt"
    )
    stage.push_command(add_cmd)
    component = add_cmd.result_component
    assert len(gr_node.plugs) == plug_count
    assert gr_node.get_plug(component) is None

    component.writable = True
    stage_editor.gr_stage.rebuild_current_scope()
    assert stage_editor.gr_stage.get_gr_node(node) is gr_node
    assert len(gr_node.plugs) == plug_count + 1
    assert gr_node.get_plug(component).component is component

    stage.undo_stack.undo()
    assert len(gr_node.plugs) == plug_count
    assert gr_node.get_plug(component) is None


def test_cutline_bounds_follow_points(qtbot):
    cutline = GraphCutLine()
    assert cutline.boundingRect().isNull()
    cutline.add_point(QtCore.QPointF(0, 0))
    cutline.add_point(QtCore.QPointF(100, 50))
    assert cutline.boundingRect().contains(QtCore.QPointF(100, 50))
    cutline.clear()
    assert cutline.boundingRect().isNull()


@pytest.mark.parametrize("target", ["title", "plug", "body"])
def test_double_click_anywhere_on_node_steps_in(
    stage_editor, create_node, qtbot, target
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    view = stage_editor.gr_view
    stage_editor.show()
    qtbot.waitExposed(stage_editor)

    if target == "title":
        scene_pos = gr_node.title_item.sceneBoundingRect().center()
    elif target == "plug":
        scene_pos = gr_node.plugs[0].sceneBoundingRect().center()
    else:
        scene_pos = gr_node.mapToScene(gr_node.width / 2, gr_node.height - 4)
    view.centerOn(gr_node)
    assert view.itemAt(view.mapFromScene(scene_pos)) is not None

    qtbot.mouseDClick(
        view.viewport(),
        QtCore.Qt.MouseButton.LeftButton,
        pos=view.mapFromScene(scene_pos),
    )
    assert stage_editor.get_scope_path() == node.path


def _node_body_point(gr_node):
    """Scene point inside the node that is neither on a plug row nor on a socket."""
    return gr_node.mapToScene(50, gr_node.height - gr_node.options.lower_padding / 2)


def _flow_plug(stage_editor, node):
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    return gr_node.get_plug(node.components_model.get_component("flow"))


def _link_flows(stage, source, target):
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage,
            source=source.components_model.get_component("flow"),
            target=target.components_model.get_component("flow"),
        )
    )


def test_graphics_stage_draws_links_between_drawn_nodes(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    assert stage_editor.gr_stage.gr_links() == []

    _link_flows(stage, a, b)
    gr_stage = stage_editor.gr_stage
    (gr_link,) = gr_stage.gr_links()
    assert gr_link.source_plug is _flow_plug(stage_editor, a)
    assert gr_link.target_plug is _flow_plug(stage_editor, b)
    assert gr_link in gr_link.source_plug.links

    stage.undo_stack.undo()
    assert gr_stage.gr_links() == []
    assert _flow_plug(stage_editor, a).links == []


def test_graphics_stage_skips_links_leaving_the_scope(stage_editor, create_node):
    stage = stage_editor.stage
    parent = create_node(stage, "parent", type_id=CoreNodes.ACTION)
    inner = create_node(stage, "inner", parent=parent, type_id=CoreNodes.ACTION)
    outer = create_node(stage, "outer", type_id=CoreNodes.ACTION)
    _link_flows(stage, outer, inner)
    assert stage_editor.gr_stage.gr_links() == []


def test_graphics_link_follows_moved_node(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    _link_flows(stage, a, b)
    gr_stage = stage_editor.gr_stage
    (gr_link,) = gr_stage.gr_links()
    before = gr_link.path().elementAt(0)
    gr_stage.get_gr_node(a).setPos(300, 200)
    after = gr_link.path().elementAt(0)
    assert (after.x, after.y) != (before.x, before.y)
    anchor = gr_link.source_plug.output_anchor()
    assert (after.x, after.y) == (anchor.x(), anchor.y())


def test_dragging_from_socket_to_socket_creates_link(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    gr_stage = stage_editor.gr_stage
    gr_stage.get_gr_node(b).setPos(400, 0)
    plug_a, plug_b = _flow_plug(stage_editor, a), _flow_plug(stage_editor, b)

    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    assert gr_stage.is_dragging_link
    gr_stage.update_link_drag(plug_b.input_anchor())
    gr_stage.finish_link_drag(plug_b.input_anchor())

    assert not gr_stage.is_dragging_link
    (gr_link,) = gr_stage.gr_links()
    assert (gr_link.source_plug, gr_link.target_plug) == (plug_a, plug_b)


def test_dragging_from_input_socket_links_in_reverse(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    gr_stage = stage_editor.gr_stage
    gr_stage.get_gr_node(b).setPos(400, 0)
    plug_a, plug_b = _flow_plug(stage_editor, a), _flow_plug(stage_editor, b)

    gr_stage.begin_link_drag(plug_b, plug_b.Socket.INPUT)
    gr_stage.finish_link_drag(plug_a.output_anchor())
    (gr_link,) = gr_stage.gr_links()
    assert (gr_link.source_plug, gr_link.target_plug) == (plug_a, plug_b)


def test_dropping_on_wrong_socket_or_node_does_not_link(
    stage_editor, create_node, monkeypatch
):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    gr_stage = stage_editor.gr_stage
    gr_stage.get_gr_node(b).setPos(400, 0)
    plug_a, plug_b = _flow_plug(stage_editor, a), _flow_plug(stage_editor, b)
    opened = []
    monkeypatch.setattr(
        gr_stage.link_drag_handler, "_open_palette", lambda *args: opened.append(args)
    )

    # output dropped on an output socket
    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    gr_stage.finish_link_drag(plug_b.output_anchor())
    # dropped on the body of a node
    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    gr_stage.finish_link_drag(_node_body_point(gr_stage.get_gr_node(b)))

    QtWidgets.QApplication.processEvents()
    assert gr_stage.gr_links() == []
    assert opened == []
    assert not gr_stage.is_dragging_link


def test_dropping_on_empty_space_opens_palette_and_links_new_node(
    stage_editor, create_node, monkeypatch, qtbot
):
    from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    gr_stage = stage_editor.gr_stage
    plug_a = _flow_plug(stage_editor, a)

    def fake_popup(on_node_spawned=None):
        command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.ACTION, name="spawned"
        )
        stage.push_command(command)
        on_node_spawned(command.result_node)

    monkeypatch.setattr(PopupNodesPalette, "popup", fake_popup)

    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    gr_stage.finish_link_drag(QtCore.QPointF(2000, 2000))
    qtbot.waitUntil(lambda: len(gr_stage.gr_links()) == 1, timeout=2000)
    (gr_link,) = gr_stage.gr_links()
    assert gr_link.source_plug is plug_a
    assert gr_link.target_plug.component.node.name == "spawned"


def test_cutline_unlinks_crossed_links_in_one_undo_step(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    c = create_node(stage, "c", type_id=CoreNodes.ACTION)
    gr_stage = stage_editor.gr_stage
    stage.push_command(
        commands.MoveNodeCommand(
            stage=stage,
            nodes=[b, c],
            new_positions=[QtCore.QPointF(400, 0), QtCore.QPointF(400, 300)],
        )
    )
    stage.undo_stack.clear()
    _link_flows(stage, a, b)
    _link_flows(stage, b, c)
    assert len(gr_stage.gr_links()) == 2

    # Line crossing only the curve between a and b
    plug_a, plug_b = _flow_plug(stage_editor, a), _flow_plug(stage_editor, b)
    start, end = plug_a.output_anchor(), plug_b.input_anchor()
    middle = (start + end) / 2
    view = stage_editor.gr_view
    view.cutline.line_points = [
        middle + QtCore.QPointF(0, -30),
        middle + QtCore.QPointF(0, 30),
    ]
    assert view.cut_intersecting_links()
    assert [g.target_plug for g in gr_stage.gr_links()] == [_flow_plug(stage_editor, c)]
    assert stage.undo_stack.count() == 3

    stage.undo_stack.undo()
    assert len(gr_stage.gr_links()) == 2


def test_cutline_missing_links_does_nothing(stage_editor, create_node):
    create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    view = stage_editor.gr_view
    view.cutline.line_points = [QtCore.QPointF(0, 0), QtCore.QPointF(50, 50)]
    assert not view.cut_intersecting_links()


def _three_nodes(stage_editor, create_node):
    stage = stage_editor.stage
    nodes = [create_node(stage, n, type_id=CoreNodes.ACTION) for n in "abc"]
    stage.push_command(
        commands.MoveNodeCommand(
            stage=stage,
            nodes=nodes[1:],
            new_positions=[QtCore.QPointF(400, 0), QtCore.QPointF(400, 300)],
        )
    )
    return nodes


def test_dragging_linked_input_socket_picks_up_the_link(stage_editor, create_node):
    a, b, c = _three_nodes(stage_editor, create_node)
    stage, gr_stage = stage_editor.stage, stage_editor.gr_stage
    _link_flows(stage, a, b)
    plug_a, plug_b, plug_c = (_flow_plug(stage_editor, n) for n in (a, b, c))
    (old_link,) = gr_stage.gr_links()

    gr_stage.begin_link_drag(plug_b, plug_b.Socket.INPUT)
    assert not old_link.isVisible()
    assert gr_stage.link_drag_handler.preview.source_plug is plug_a

    # Dropped on empty node body: cancelled, old link is back
    gr_stage.finish_link_drag(_node_body_point(gr_stage.get_gr_node(c)))
    assert old_link.isVisible()
    assert [g.target_plug for g in gr_stage.gr_links()] == [plug_b]

    # Dropped on the same input: no change, nothing pushed
    count = stage.undo_stack.count()
    gr_stage.begin_link_drag(plug_b, plug_b.Socket.INPUT)
    gr_stage.finish_link_drag(plug_b.input_anchor())
    assert stage.undo_stack.count() == count

    # Dropped on another input: link moves, in one undo step
    gr_stage.begin_link_drag(plug_b, plug_b.Socket.INPUT)
    gr_stage.finish_link_drag(plug_c.input_anchor())
    (moved,) = gr_stage.gr_links()
    assert (moved.source_plug, moved.target_plug) == (plug_a, plug_c)
    assert stage.undo_stack.count() == count + 1

    stage.undo_stack.undo()
    (restored,) = gr_stage.gr_links()
    assert (restored.source_plug, restored.target_plug) == (plug_a, plug_b)


def test_moved_link_dropped_on_empty_space_replaced_by_spawned_node_link(
    stage_editor, create_node, monkeypatch, qtbot
):
    from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

    a, b, _ = _three_nodes(stage_editor, create_node)
    stage, gr_stage = stage_editor.stage, stage_editor.gr_stage
    _link_flows(stage, a, b)
    plug_b = _flow_plug(stage_editor, b)

    def fake_popup(on_node_spawned=None):
        command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.ACTION, name="spawned"
        )
        stage.push_command(command)
        on_node_spawned(command.result_node)

    monkeypatch.setattr(PopupNodesPalette, "popup", fake_popup)
    gr_stage.begin_link_drag(plug_b, plug_b.Socket.INPUT)
    gr_stage.finish_link_drag(QtCore.QPointF(2000, 2000))
    qtbot.waitUntil(
        lambda: [g.target_plug.component.node.name for g in gr_stage.gr_links()]
        == ["spawned"],
        timeout=2000,
    )


def test_view_is_in_link_drag_mode_only_while_dragging(
    stage_editor, create_node, give_focus, monkeypatch
):
    a = create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    view, gr_stage = stage_editor.gr_view, stage_editor.gr_stage
    give_focus(view)
    plug = _flow_plug(stage_editor, a)
    palette_action = ACTION_REGISTRY.action(ActionId.SHOW_PALETTE)
    create_action = ACTION_REGISTRY.action(ActionId.CREATE_NODE)
    menus = []
    monkeypatch.setattr(context_menus, "show_menu", lambda menu, pos: menus.append(menu))
    assert view.is_idle and palette_action.isEnabled() and create_action.isEnabled()

    gr_stage.begin_link_drag(plug, plug.Socket.OUTPUT)
    assert view.interaction_mode is view.InteractionMode.LINK_DRAG
    assert not palette_action.isEnabled()
    assert not create_action.isEnabled()
    view.show_context_menu(QtCore.QPoint(5, 5))
    assert menus == []

    gr_stage.finish_link_drag(plug.output_anchor())
    assert view.is_idle
    assert palette_action.isEnabled() and create_action.isEnabled()
    view.show_context_menu(QtCore.QPoint(5, 5))
    assert len(menus) == 1


def test_cancelled_link_drag_returns_view_to_idle(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    plug = _flow_plug(stage_editor, a)
    stage_editor.gr_stage.begin_link_drag(plug, plug.Socket.OUTPUT)
    stage_editor.gr_stage.cancel_link_drag()
    assert stage_editor.gr_view.is_idle


def test_undo_and_redo_are_disabled_while_not_idle(
    main_window, stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    undo_actions = list(ACTION_REGISTRY.iter_live_actions(ActionId.UNDO))
    assert undo_actions and all(action.isEnabled() for action in undo_actions)
    view, gr_stage = stage_editor.gr_view, stage_editor.gr_stage
    plug = _flow_plug(stage_editor, a)

    gr_stage.begin_link_drag(plug, plug.Socket.OUTPUT)
    assert not any(action.isEnabled() for action in undo_actions)
    gr_stage.cancel_link_drag()
    assert all(action.isEnabled() for action in undo_actions)
    assert main_window.undo_group.activeStack() is stage_editor.stage.undo_stack

    view.set_interaction_mode(view.InteractionMode.LINK_CUT)
    assert not any(action.isEnabled() for action in undo_actions)
    view.set_interaction_mode(view.InteractionMode.NOOP)
    assert all(action.isEnabled() for action in undo_actions)


def test_dropped_link_reaches_undo_group_listeners(
    main_window, stage_editor, create_node
):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.MoveNodeCommand(
            stage=stage, nodes=[b], new_positions=[QtCore.QPointF(400, 0)]
        )
    )
    plug_a, plug_b = _flow_plug(stage_editor, a), _flow_plug(stage_editor, b)
    indexes = []
    main_window.undo_group.indexChanged.connect(indexes.append)

    stage_editor.gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    stage_editor.gr_stage.finish_link_drag(plug_b.input_anchor())
    # The group also reports the stack leaving and returning, the link comes last.
    assert indexes[-1] == stage.undo_stack.index()
    assert stage.undo_stack.index() == stage.undo_stack.count()


def test_view_state_reflects_mode_and_selection(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    view = stage_editor.gr_view
    context = view.get_current_state()
    assert (context.is_idle, context.has_selection) == (True, False)
    assert not context.can_edit_selection

    select(stage_editor, a)
    assert view.get_current_state().can_edit_selection

    view.set_interaction_mode(view.InteractionMode.LINK_CUT)
    context = view.get_current_state()
    assert (context.is_idle, context.has_selection) == (False, True)
    assert not context.can_edit_selection


def test_dragging_single_output_socket_picks_up_its_link(stage_editor, create_node):
    a, b, c = _three_nodes(stage_editor, create_node)
    stage, gr_stage = stage_editor.stage, stage_editor.gr_stage
    _link_flows(stage, a, b)
    plug_a, plug_b, plug_c = (_flow_plug(stage_editor, n) for n in (a, b, c))
    (old_link,) = gr_stage.gr_links()

    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    assert not old_link.isVisible()
    assert gr_stage.link_drag_handler.preview.target_plug is plug_b

    # Dropped on a node body: cancelled, old link is back
    gr_stage.finish_link_drag(_node_body_point(gr_stage.get_gr_node(c)))
    assert old_link.isVisible()
    assert [g.source_plug for g in gr_stage.gr_links()] == [plug_a]


def test_single_output_link_dropped_on_other_output_moves_in_one_undo_step(
    stage_editor, create_node
):
    a, b, c = _three_nodes(stage_editor, create_node)
    stage, gr_stage = stage_editor.stage, stage_editor.gr_stage
    _link_flows(stage, a, b)
    plug_a, plug_b, plug_c = (_flow_plug(stage_editor, n) for n in (a, b, c))
    count = stage.undo_stack.count()

    gr_stage.begin_link_drag(plug_a, plug_a.Socket.OUTPUT)
    gr_stage.finish_link_drag(plug_c.output_anchor())
    (moved,) = gr_stage.gr_links()
    assert (moved.source_plug, moved.target_plug) == (plug_c, plug_b)
    assert stage.undo_stack.count() == count + 1

    stage.undo_stack.undo()
    (restored,) = gr_stage.gr_links()
    assert (restored.source_plug, restored.target_plug) == (plug_a, plug_b)


def test_dragging_to_a_single_output_source_replaces_its_link(stage_editor, create_node):
    a, b, c = _three_nodes(stage_editor, create_node)
    stage, gr_stage = stage_editor.stage, stage_editor.gr_stage
    _link_flows(stage, a, b)
    plug_a, plug_b, plug_c = (_flow_plug(stage_editor, n) for n in (a, b, c))

    # Output of a is taken by the link to b: a new one from the input of c replaces it
    gr_stage.begin_link_drag(plug_c, plug_c.Socket.INPUT)
    gr_stage.finish_link_drag(plug_a.output_anchor())
    (replacing,) = gr_stage.gr_links()
    assert (replacing.source_plug, replacing.target_plug) == (plug_a, plug_c)
    assert len(a["flow"].output_links) == 1


def test_node_without_plugs_is_as_tall_as_a_single_plug_row(stage_editor, create_node):
    from nyx.editor.graphics.graphics_plug import GraphicsPlug

    node = create_node(stage_editor.stage, "empty", type_id=CoreNodes.EMPTY)
    gr_node = stage_editor.gr_stage.get_gr_node(node)

    assert not gr_node.plugs
    assert gr_node.height == (
        gr_node.title_height
        + gr_node.options.plugs_top_padding
        + GraphicsPlug.ROW_HEIGHT
        + gr_node.options.lower_padding
    )
    assert gr_node.height < 100


def test_node_grows_by_a_row_per_plug_row_beyond_the_first(stage_editor, create_node):
    from nyx.editor.graphics.graphics_plug import GraphicsPlug

    stage = stage_editor.stage
    single = stage_editor.gr_stage.get_gr_node(
        create_node(stage, "single", type_id=CoreNodes.FLOW_START)
    )
    branch = stage_editor.gr_stage.get_gr_node(
        create_node(stage, "branch", type_id=CoreNodes.BRANCH)
    )

    assert len(single.plugs) == 1
    assert len(branch.plugs) == 4
    # inputs and outputs share rows: flow | true and condition | false
    assert branch.height - single.height == 1 * GraphicsPlug.ROW_HEIGHT


def test_input_and_output_only_plugs_share_rows(stage_editor, create_node):
    stage = stage_editor.stage
    gr_node = stage_editor.gr_stage.get_gr_node(
        create_node(stage, "branch", type_id=CoreNodes.BRANCH)
    )
    flow, true, false, condition = gr_node.plugs

    assert flow.pos().y() == true.pos().y()
    assert condition.pos().y() == false.pos().y()
    assert condition.pos().y() > flow.pos().y()
    for input_plug in (flow, condition):
        assert input_plug.is_writable and not input_plug.is_readable
        assert input_plug.pos().x() == 0.0
    for output_plug in (true, false):
        assert output_plug.is_readable and not output_plug.is_writable
        assert output_plug.pos().x() > 0.0
        assert (
            output_plug.pos().x() + output_plug.boundingRect().width() == gr_node.width
        )


def test_plug_with_both_sockets_takes_a_row_alone(stage_editor, create_node):
    stage = stage_editor.stage
    gr_node = stage_editor.gr_stage.get_gr_node(
        create_node(stage, "branch", type_id=CoreNodes.BRANCH)
    )
    flow, true, false, condition = gr_node.plugs
    condition.component.readable = True
    gr_node.refresh()

    assert condition.is_writable and condition.is_readable
    others = {flow.pos().y(), true.pos().y(), false.pos().y()}
    assert condition.pos().y() not in others
    assert condition.pos().x() == 0.0
    assert condition.boundingRect().width() == gr_node.width
