import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes, commands
from nyx.editor.views.node_components_view import NodeComponentsView


def texts(item):
    """Every text shown by the items below an item."""
    found = []
    value = item.property("text")
    if isinstance(value, str):
        found.append(value)
    for child in item.childItems():
        found.extend(texts(child))
    return found


@pytest.fixture
def remote_client_gr_node(main_window, stage_editor, create_node):
    node = create_node(
        stage_editor.stage, "remote_client", type_id=CoreNodes.REMOTE_CLIENT
    )
    return node, stage_editor.gr_stage.get_gr_node(node)


@pytest.fixture(autouse=True)
def show_display_names(main_window, qapp):
    """Start every test with display names shown, as the config default says."""
    main_window._apply_show_address_names()
    yield
    qapp.session.set_show_address_names(False)
    main_window._apply_show_address_names()


def titled(gr_node):
    return gr_node.title_item.toPlainText()


def test_view_menu_toggle_switches_titles_and_plug_labels(
    main_window, stage_editor, remote_client_gr_node, qapp, monkeypatch
):
    node, gr_node = remote_client_gr_node
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    stage_editor.stage.push_command(
        commands.RenameNodeCommand(stage_editor.stage, node, "My Client")
    )
    plug = next(p for p in gr_node.plugs if p._component.name == "client_name")
    action = main_window.menubar_view_menu.show_address_names_action
    assert not action.isChecked()
    assert (titled(gr_node), plug._label) == ("My Client", "Client Name")

    action.trigger()

    assert qapp.session.show_address_names
    assert qapp.config.values.editor_behaviour.show_address_names
    assert stage_editor.stage.show_address_names
    assert (titled(gr_node), plug._label) == ("my_client", "client_name")

    action.trigger()
    assert (titled(gr_node), plug._label) == ("My Client", "Client Name")


def test_new_stages_follow_the_setting(main_window, qapp, monkeypatch):
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    qapp.session.set_show_address_names(True)

    main_window.on_stage_new()

    assert main_window.current_stage_graph.stage.show_address_names


def test_menu_shows_the_configured_setting(main_window, qapp, monkeypatch):
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    qapp.session.set_show_address_names(True)

    main_window.apply_config_values()

    assert main_window.menubar_view_menu.show_address_names_action.isChecked()


def test_title_edit_renames_through_the_display_name(
    stage_editor, remote_client_gr_node
):
    node, gr_node = remote_client_gr_node

    gr_node.title_item.apply_edit("  My cool node ")

    assert (node.display_name, node.name) == ("My cool node", "my_cool_node")
    assert titled(gr_node) == "My cool node"
    stage_editor.stage.undo_stack.undo()
    assert (node.display_name, node.name) == ("Remote Client", "remote_client")
    assert titled(gr_node) == "Remote Client"


def test_title_edit_ignores_unchanged_and_unusable_names(
    stage_editor, remote_client_gr_node
):
    node, gr_node = remote_client_gr_node
    count = stage_editor.stage.undo_stack.count()

    gr_node.title_item.apply_edit("Remote Client")
    gr_node.title_item.apply_edit("???")

    assert stage_editor.stage.undo_stack.count() == count
    assert node.name == "remote_client"


def test_title_tooltip_names_both(remote_client_gr_node):
    _, gr_node = remote_client_gr_node

    tooltip = gr_node.title_item.toolTip()

    assert "Remote Client" in tooltip and "remote_client" in tooltip


def test_inspector_header_edits_the_display_name(
    main_window, stage_editor, remote_client_gr_node, qtbot
):
    node, _ = remote_client_gr_node
    header = main_window.inspector._node_header
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    qtbot.waitUntil(lambda: header.name_field.text() == "Remote Client", timeout=3000)
    assert "remote_client" in header.name_field.toolTip()

    header.name_field.setText("My cool node")
    header._on_name_edited()

    assert (node.display_name, node.name) == ("My cool node", "my_cool_node")


def test_component_rows_show_labels_and_switch_with_the_setting(
    main_window, stage_editor, remote_client_gr_node, qtbot
):
    node, _ = remote_client_gr_node
    main_window.inspector.show()
    main_window.inspector.resize(500, 700)
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    root = view.rootObject()

    qtbot.waitUntil(lambda: "Client Name" in texts(root), timeout=3000)
    stage_editor.stage.show_address_names = True

    qtbot.waitUntil(lambda: "client_name" in texts(root), timeout=3000)
    assert "Client Name" not in texts(root)


def test_component_row_rename_sets_the_display_name(
    main_window, stage_editor, remote_client_gr_node, qtbot
):
    node, _ = remote_client_gr_node
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)
    controller = view.rootObject().property("componentsController")
    proxy = controller.components_filter_model
    component = node["client_name"]
    row = next(
        row
        for row in range(proxy.rowCount())
        if controller.get_component_from_proxy_row(row) is component
    )

    controller.renameComponent(row, "Who to wait for")

    assert component.display_name == "Who to wait for"
    assert component.name == "who_to_wait_for"
    qtbot.waitUntil(lambda: "Who to wait for" in texts(view.rootObject()), timeout=3000)


def test_toggle_rebuilds_the_current_scope_of_every_editor(
    main_window, stage_editor, qapp, monkeypatch
):
    rebuilt = []
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        stage_editor.gr_stage,
        "rebuild_current_scope",
        lambda: rebuilt.append(stage_editor),
    )

    main_window.set_show_address_names(True)

    assert rebuilt == [stage_editor]


def test_toggle_shows_the_names_of_the_nodes_of_the_current_scope(
    main_window, stage_editor, create_node, qapp, monkeypatch
):
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    stage = stage_editor.stage
    group = create_node(stage, "group")
    inner = create_node(stage, "inner", parent=group.path)
    stage.push_command(commands.RenameNodeCommand(stage, inner, "Inner Node"))
    stage_editor.set_scope_path(group.path)
    gr_inner = stage_editor.gr_stage.get_gr_node(inner)
    assert titled(gr_inner) == "Inner Node"

    main_window.set_show_address_names(True)
    assert titled(stage_editor.gr_stage.get_gr_node(inner)) == "inner_node"

    main_window.set_show_address_names(False)
    assert titled(stage_editor.gr_stage.get_gr_node(inner)) == "Inner Node"
