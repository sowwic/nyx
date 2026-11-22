import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import (
    CoreNodeComponents,
    CoreNodes,
    Node,
    NodeComponent,
    Stage,
    commands,
)
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.editor.views.tree_branch_lines import BranchLinesMixin
from nyx.editor.widgets.dialogs.stage_object_picker import StageObjectPickerDialog
from stage_helpers import STAGES
from nyx.editor.panels.panel_definitions import PanelId

"""Stages of the running test: a node doesn't keep its stage alive."""


def create(stage, type_id=CoreNodes.EMPTY, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


@pytest.fixture
def stage():
    """Stage with /stage/a (components flow-less, one value) and /stage/group/b."""
    stage = Stage()
    STAGES.append(stage)
    a = create(stage, CoreNodes.VALUE, name="a")
    group = create(stage, name="group")
    create(stage, CoreNodes.VALUE, parent=group.path, name="b")
    stage.a, stage.group = a, group
    return stage


def dialog_for(stage, qtbot, **kwargs):
    dialog = StageObjectPickerDialog(stage, **kwargs)
    qtbot.addWidget(dialog)
    return dialog


def item_for(dialog, stage_object):
    return dialog.tree.item_for(stage_object)


def ok_enabled(dialog):
    return dialog.buttons.button(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
    ).isEnabled()


def visible_paths(dialog):
    return {item.text(1) for item in dialog.tree.listed_items() if not item.isHidden()}


def test_tree_lists_nodes_with_their_components_below(stage, qtbot):
    dialog = dialog_for(stage, qtbot)

    node_item = item_for(dialog, stage.a)
    component_item = item_for(dialog, stage.a["value"])

    assert node_item.text(1) == "/stage/a"
    assert component_item.parent() is node_item
    assert component_item.text(0) == stage.a["value"].label
    assert item_for(dialog, stage.group).parent() is item_for(dialog, stage.root_node)
    assert item_for(dialog, stage.group).childCount() >= 1


def test_labels_follow_the_address_name_setting(stage, qtbot):
    stage.push_command(commands.RenameNodeCommand(stage, stage.a, "My value"))
    shown = dialog_for(stage, qtbot)
    assert item_for(shown, stage.a).text(0) == "My value"

    stage.show_address_names = True

    assert item_for(dialog_for(stage, qtbot), stage.a).text(0) == "my_value"


def test_only_what_the_target_types_allow_can_be_chosen(stage, qtbot):
    nodes_only = dialog_for(stage, qtbot, target_types=(Node,))
    components_only = dialog_for(stage, qtbot, target_types=(NodeComponent,))

    assert item_for(nodes_only, stage.a).flags() & QtCore.Qt.ItemFlag.ItemIsSelectable
    assert nodes_only.tree.item_for(stage.a["value"]) is None
    assert not (
        item_for(components_only, stage.a).flags() & QtCore.Qt.ItemFlag.ItemIsSelectable
    )
    assert item_for(components_only, stage.a["value"]).flags() & (
        QtCore.Qt.ItemFlag.ItemIsSelectable
    )


def test_choosing_returns_the_object_and_ok_needs_a_choice(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    assert not ok_enabled(dialog)
    assert dialog.selected_object is None

    dialog.tree.setCurrentItem(item_for(dialog, stage.a["value"]))

    assert ok_enabled(dialog)
    assert dialog.selected_object is stage.a["value"]


def test_an_item_that_cannot_be_chosen_does_not_enable_ok(stage, qtbot):
    dialog = dialog_for(stage, qtbot, target_types=(NodeComponent,))

    dialog.tree.setCurrentItem(item_for(dialog, stage.a))

    assert dialog.selected_object is None
    assert not ok_enabled(dialog)


def test_it_starts_at_the_current_target(stage, qtbot):
    dialog = dialog_for(stage, qtbot, current_target=stage.a)

    assert dialog.selected_object is stage.a
    assert ok_enabled(dialog)


def test_a_current_target_that_cannot_be_chosen_is_not_selected(stage, qtbot):
    dialog = dialog_for(
        stage, qtbot, target_types=(Node,), current_target=stage.a["value"]
    )

    assert dialog.selected_object is None


def test_search_keeps_matches_and_the_items_leading_to_them(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    b = stage.group.list_children()[0]

    dialog.search_field.setText("group/b")

    shown = visible_paths(dialog)
    assert b.path.as_posix() in shown
    assert stage.group.path.as_posix() in shown
    assert stage.root_node.path.as_posix() in shown
    assert stage.a.path.as_posix() not in shown
    assert item_for(dialog, stage.group).isExpanded()

    dialog.search_field.setText("")
    assert stage.a.path.as_posix() in visible_paths(dialog)


def test_search_matches_the_name_in_either_form(stage, qtbot):
    stage.push_command(commands.RenameNodeCommand(stage, stage.a, "Fancy Thing"))
    dialog = dialog_for(stage, qtbot)

    dialog.search_field.setText("fancy")
    assert stage.a.path.as_posix() in visible_paths(dialog)

    dialog.search_field.setText("fancy_thing")
    assert stage.a.path.as_posix() in visible_paths(dialog)

    dialog.search_field.setText("nothing like this")
    assert visible_paths(dialog) == set()


def test_double_clicking_a_choosable_item_accepts(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    item = item_for(dialog, stage.a)
    dialog.tree.setCurrentItem(item)

    dialog.tree.itemDoubleClicked.emit(item, 0)

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_object is stage.a


def test_double_clicking_what_cannot_be_chosen_does_not_accept(stage, qtbot):
    dialog = dialog_for(stage, qtbot, target_types=(NodeComponent,))

    dialog.tree.itemDoubleClicked.emit(item_for(dialog, stage.a), 0)

    assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted


# The path component, its controller and its QML button


@pytest.fixture
def path_view(main_window, stage_editor, create_node, qtbot):
    """Inspector showing /stage/holder with a path component, and the nodes around."""
    stage = stage_editor.stage
    target = create_node(stage, "target", type_id=CoreNodes.VALUE)
    holder = create_node(stage, "holder", type_id=CoreNodes.EMPTY)
    stage.push_command(
        commands.AddNodeComponentCommand(
            node=holder, type_id=CoreNodeComponents.STAGE_OBJECT_PATH, name="where"
        )
    )
    main_window.panel_manager.set_open(PanelId.INSPECTOR, True)
    main_window.panel_host.set_panel_size(
        main_window.panel_manager.panel(PanelId.INSPECTOR), 600
    )
    stage_editor.selection_model.select(
        holder.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    root = view.rootObject()
    list_view = root.findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)
    controller = root.property("componentsController")
    component = holder["where"]
    proxy = controller.components_filter_model
    row = next(
        row
        for row in range(proxy.rowCount())
        if controller.get_component_from_proxy_row(row) is component
    )
    return view, controller, row, component, target


def patch_picker(monkeypatch, chosen):
    calls = []

    def pick(stage, component, parent=None):
        calls.append(component)
        return chosen

    monkeypatch.setattr(StageObjectPickerDialog, "pick", staticmethod(pick))
    return calls


def test_controller_returns_the_path_relative_to_the_scope(path_view, monkeypatch):
    _, controller, row, component, target = path_view
    calls = patch_picker(monkeypatch, target)

    assert controller.pickStageObjectPath(row) == "target"
    assert calls == [component]


def test_controller_returns_component_paths_with_their_suffix(path_view, monkeypatch):
    _, controller, row, _, target = path_view
    patch_picker(monkeypatch, target["value"])

    assert controller.pickStageObjectPath(row) == "target.value"


def test_controller_goes_up_for_objects_outside_the_scope(
    path_view, create_node, monkeypatch
):
    _, controller, row, component, target = path_view
    stage = component.stage
    inner = create_node(stage, "inner", parent=component.node.path)
    # The scope of the holder is /stage, so the way to its child goes through it.
    patch_picker(monkeypatch, inner)

    assert controller.pickStageObjectPath(row) == "holder/inner"


def test_controller_returns_nothing_when_cancelled(path_view, monkeypatch):
    _, controller, row, _, _ = path_view
    patch_picker(monkeypatch, None)

    assert controller.pickStageObjectPath(row) == ""


def find_by_object_name(item, name):
    found = [item] if item.objectName() == name else []
    for child in item.childItems():
        found.extend(find_by_object_name(child, name))
    return found


def test_browse_button_sets_the_path_of_the_component(path_view, monkeypatch, qtbot):
    view, _, _, component, target = path_view
    patch_picker(monkeypatch, target)
    qtbot.waitUntil(
        lambda: bool(find_by_object_name(view.rootObject(), "browseStageObjectButton")),
        timeout=3000,
    )
    button = find_by_object_name(view.rootObject(), "browseStageObjectButton")[0]
    assert button.property("enabled")

    QtCore.QMetaObject.invokeMethod(
        button, "click", QtCore.Qt.ConnectionType.DirectConnection
    )

    qtbot.waitUntil(lambda: component.target is target, timeout=3000)
    assert component.raw_value == "target"
    assert component.is_valid


def test_tree_draws_the_lines_between_its_rows(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    tree = dialog.tree
    assert isinstance(tree, BranchLinesMixin)

    root = tree.get_branch_lines(tree.indexFromItem(item_for(dialog, stage.root_node)))
    a = tree.get_branch_lines(tree.indexFromItem(item_for(dialog, stage.a)))
    group = tree.get_branch_lines(tree.indexFromItem(item_for(dialog, stage.group)))

    assert root.own_level is None
    assert (a.depth, a.has_next_sibling) == (1, True)
    assert (group.depth, group.has_next_sibling) == (1, False)


def test_a_component_row_passes_the_line_of_its_node_when_a_sibling_follows(
    stage, qtbot
):
    dialog = dialog_for(stage, qtbot)
    tree = dialog.tree

    component = tree.get_branch_lines(
        tree.indexFromItem(item_for(dialog, stage.a["value"]))
    )

    assert component.depth == 2
    assert component.passing_levels == (0,)


def test_the_lines_are_painted_in_the_dialog(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    tree = dialog.tree
    image = tree.viewport().grab().toImage()
    line = tree.palette().color(tree.BRANCH_LINE_ROLE).rgb()
    rect = tree.visualRect(tree.indexFromItem(item_for(dialog, stage.a)))

    # `a` has `group` after it, so the trunk under the arrow of the root goes on
    assert image.pixelColor(tree.indentation() // 2, rect.bottom()).rgb() == line


def icon_image(icon):
    return icon.pixmap(16, 16).toImage()


def test_every_item_shows_the_icon_of_its_type(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    value = stage.a["value"]

    node_icon = item_for(dialog, stage.a).icon(0)
    component_icon = item_for(dialog, value).icon(0)

    assert not node_icon.isNull()
    assert icon_image(node_icon) == icon_image(QtGui.QIcon(stage.a.get_type_icon()))
    assert icon_image(component_icon) == icon_image(QtGui.QIcon(value.get_type_icon()))


def test_the_tree_sets_up_its_own_columns_and_rows(stage, qtbot):
    dialog = dialog_for(stage, qtbot)
    tree = dialog.tree

    assert tree.columnCount() == len(tree.COLUMNS)
    headers = [tree.headerItem().text(i) for i in range(tree.columnCount())]
    assert headers == list(tree.COLUMNS)
    assert tree.iconSize() == tree.ICON_SIZE
    assert tree.uniformRowHeights()


def test_excluded_objects_are_listed_but_cannot_be_chosen(stage, qtbot):
    value = stage.a["value"]
    dialog = dialog_for(stage, qtbot, excluded=(value,))

    dialog.tree.setCurrentItem(item_for(dialog, value))

    assert item_for(dialog, value) is not None
    assert dialog.selected_object is None
    assert not ok_enabled(dialog)
    # What else is there can still be chosen
    dialog.tree.setCurrentItem(item_for(dialog, stage.a))
    assert dialog.selected_object is stage.a


def test_picking_for_a_path_component_does_not_offer_the_components_of_its_node(
    stage, qtbot, monkeypatch
):
    getter = create(stage, CoreNodes.GET, name="getter")
    component = getter["component"]
    seen = []

    def fake_exec(dialog):
        seen.append(dialog)
        return QtWidgets.QDialog.DialogCode.Rejected

    monkeypatch.setattr(StageObjectPickerDialog, "exec", fake_exec)

    assert StageObjectPickerDialog.pick(stage, component) is None

    (dialog,) = seen
    qtbot.addWidget(dialog)
    # Itself and the other components of its node are listed, and can't be chosen
    for own in (component, getter["value"]):
        assert item_for(dialog, own) is not None
        assert not dialog.tree.is_selectable(item_for(dialog, own))
    # Components of other nodes can be, a getter takes components only
    assert dialog.tree.is_selectable(item_for(dialog, stage.a["value"]))
    assert not dialog.tree.is_selectable(item_for(dialog, getter))
