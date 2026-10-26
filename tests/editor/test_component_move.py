import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodeComponents, CoreNodes, commands
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.static.paths import PACKAGE_ROOT

DELEGATE_QML = (
    PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "ComponentsView"
    / "NodeComponentDelegate.qml"
)  # fmt: skip


@pytest.fixture
def controller_and_node(main_window, stage_editor, create_node, qtbot):
    """Controller of the inspector, showing an action node with three components.

    The rows are the built-in flow, then one, two and three.
    """
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    for name in ("one", "two", "three"):
        stage.push_command(
            commands.AddNodeComponentCommand(
                node=node, type_id=CoreNodeComponents.VALUE, name=name
            )
        )
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 3, timeout=3000)
    return view.rootObject().property("componentsController"), node


def names(node):
    return [component.name for component in node.components_model.list_components()]


def test_components_can_move_between_the_custom_ones(controller_and_node):
    controller, _node = controller_and_node

    assert controller.canMoveComponent(2, -1)
    assert controller.canMoveComponent(2, 1)
    assert controller.canMoveComponent(1, 1)
    assert controller.canMoveComponent(3, -1)


def test_components_cant_move_onto_built_in_ones_or_off_the_ends(controller_and_node):
    controller, _node = controller_and_node

    assert not controller.canMoveComponent(1, -1)  # the row above is built-in
    assert not controller.canMoveComponent(3, 1)  # nothing below
    assert not controller.canMoveComponent(0, 1)  # built-in itself
    assert not controller.canMoveComponent(1, 5)


def test_move_component_up_and_down_is_undoable(controller_and_node):
    controller, node = controller_and_node
    stage = node.stage

    controller.moveComponent(2, -1)
    assert names(node) == ["flow", "two", "one", "three"]
    controller.moveComponent(1, 1)
    assert names(node) == ["flow", "one", "two", "three"]

    stage.undo_stack.undo()
    assert names(node) == ["flow", "two", "one", "three"]
    stage.undo_stack.undo()
    assert names(node) == ["flow", "one", "two", "three"]


def test_move_component_that_cant_move_does_nothing(controller_and_node):
    controller, node = controller_and_node
    stack_size = node.stage.undo_stack.count()

    controller.moveComponent(1, -1)
    controller.moveComponent(3, 1)

    assert names(node) == ["flow", "one", "two", "three"]
    assert node.stage.undo_stack.count() == stack_size


def test_components_of_a_locked_node_cant_move(
    main_window, stage_editor, create_node, qtbot, tmp_path
):
    from nyx.api.v1 import Stage

    source = Stage()
    source.push_command(
        commands.CreateNodeCommand(stage=source, type_id=CoreNodes.ACTION, name="inner")
    )
    path = tmp_path / f"source{Stage.FILE_EXTENSION}"
    source.export_json(path)
    stage = stage_editor.stage
    reference = create_node(stage, "ref", type_id=CoreNodes.REFERENCE)
    reference["source"].push_value(str(path))
    inner = reference.find_child_by_name("inner")
    for name in ("one", "two"):
        component = inner.components_model.create_component(CoreNodeComponents.VALUE)
        component.name = name
        inner.components_model.add_component(component)
    main_window.inspector.show()
    stage_editor.selection_model.select(
        inner.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    controller = view.rootObject().property("componentsController")
    qtbot.waitUntil(lambda: controller.property("structureEditable") is False)

    assert not controller.canMoveComponent(1, 1)
    controller.moveComponent(1, 1)
    assert names(inner) == ["flow", "one", "two"]


def test_options_menu_has_move_entries_for_movable_components():
    source = DELEGATE_QML.read_text()

    assert 'text: "Move Up"' in source
    assert 'text: "Move Down"' in source
    assert source.index('text: "Rename"') < source.index('text: "Move Up"')
    assert source.index('text: "Move Down"') < source.index('text: "Writable"')
