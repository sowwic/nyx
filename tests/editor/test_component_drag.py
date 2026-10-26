import pytest
from PySide6 import QtCore, QtTest

from nyx.api.v1 import CoreNodeComponents, CoreNodes, commands
from nyx.editor.views.node_components_view import NodeComponentsView


def find_items(item, object_name):
    """Find the items called `object_name` below an item, delegates included."""
    found = [item] if item.objectName() == object_name else []
    for child in item.childItems():
        found.extend(find_items(child, object_name))
    return found


@pytest.fixture
def three_components(main_window, stage_editor, create_node, qtbot):
    """View of the inspector showing a blank node with the components one, two, three."""
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.EMPTY)
    for name in ("one", "two", "three"):
        stage.push_command(
            commands.AddNodeComponentCommand(
                node=node, type_id=CoreNodeComponents.VALUE, name=name
            )
        )
    main_window.inspector.show()
    main_window.inspector.resize(500, 700)
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") == 3, timeout=3000)
    qtbot.wait(300)
    return view, node


def names(node):
    return [component.name for component in node.components_model.list_components()]


def grip_position(view, row):
    """Scene position of the drag grip of the row-th component, counted from the top."""
    handles = find_items(view.rootObject(), "rowDragHandler")
    handles.sort(key=lambda handle: handle.mapToScene(QtCore.QPointF(0, 0)).y())
    handle = handles[row]
    return handle.mapToScene(QtCore.QPointF(handle.width() - 6, handle.height() / 2))


def drag(view, qtbot, start, end, steps=12):
    """Drag with the left mouse button from a position to another and release."""
    QtTest.QTest.mousePress(
        view, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, start.toPoint()
    )
    qtbot.wait(30)
    for step in range(1, steps + 1):
        point = start + (end - start) * (step / steps)
        QtTest.QTest.mouseMove(view, point.toPoint())
        qtbot.wait(20)
    QtTest.QTest.mouseRelease(
        view, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, end.toPoint()
    )
    qtbot.wait(400)


def test_the_first_component_can_be_dragged_to_the_bottom_again_and_again(
    three_components, qtbot
):
    view, node = three_components
    expected_orders = [
        ["two", "three", "one"],
        ["three", "one", "two"],
        ["one", "two", "three"],
    ]

    for expected in expected_orders:
        start = grip_position(view, 0)
        end = grip_position(view, 2) + QtCore.QPointF(0, 60)
        drag(view, qtbot, start, end)

        assert names(node) == expected


def test_the_last_component_can_be_dragged_to_the_top_again_and_again(
    three_components, qtbot
):
    view, node = three_components
    expected_orders = [
        ["three", "one", "two"],
        ["two", "three", "one"],
        ["one", "two", "three"],
    ]

    for expected in expected_orders:
        start = grip_position(view, 2)
        end = grip_position(view, 0) - QtCore.QPointF(0, 60)
        drag(view, qtbot, start, end)

        assert names(node) == expected
