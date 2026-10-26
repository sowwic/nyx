import pytest
from PySide6 import QtCore, QtQml, QtTest

from nyx.api.v1 import CoreNodes, commands
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.static.paths import PACKAGE_ROOT

LINK_DELEGATE_QML = (
    PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "ComponentsView"
    / "LinkItemDelegate.qml"
)  # fmt: skip


@pytest.fixture
def linked(main_window, stage_editor, create_node, qtbot):
    """Controller of the inspector showing `target`, whose value is fed by `source`."""
    stage = stage_editor.stage
    source = create_node(stage, "source", type_id=CoreNodes.VALUE)
    target = create_node(stage, "target", type_id=CoreNodes.VALUE)
    target["value"].writable = True
    link_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=source["value"], target=target["value"]
    )
    stage.push_command(link_command)

    main_window.inspector.show()
    stage_editor.selection_model.select(
        target.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)
    controller = view.rootObject().property("componentsController")
    proxy = controller.components_filter_model
    row = next(
        row
        for row in range(proxy.rowCount())
        if controller.get_component_from_proxy_row(row) is target["value"]
    )
    controller.view_root = view.rootObject()
    return controller, row, source, target, stage


def test_unlinking_removes_the_input_link(linked):
    controller, row, source, target, stage = linked
    assert target["value"].input_links

    assert controller.unlinkComponent(row, "Input", source["value"].path.as_posix())

    assert target["value"].input_links == []
    assert source["value"].output_links == []


def test_unlinking_can_be_undone(linked):
    controller, row, source, target, stage = linked
    controller.unlinkComponent(row, "Input", source["value"].path.as_posix())

    stage.undo_stack.undo()

    assert len(target["value"].input_links) == 1


def test_unlinking_the_output_side(linked, main_window, stage_editor, qtbot):
    controller, _row, source, target, stage = linked
    stage_editor.selection_model.clearSelection()
    stage_editor.selection_model.select(
        source.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    qtbot.waitUntil(
        lambda: controller.components_model is not None
        and controller.components_model.node is source,
        timeout=3000,
    )
    proxy = controller.components_filter_model
    row = next(
        row
        for row in range(proxy.rowCount())
        if controller.get_component_from_proxy_row(row) is source["value"]
    )

    assert controller.unlinkComponent(row, "Output", target["value"].path.as_posix())

    assert source["value"].output_links == []


def test_unlinking_an_unknown_path_changes_nothing(linked, caplog):
    controller, row, _source, target, stage = linked
    count = stage.undo_stack.count()

    with caplog.at_level("WARNING"):
        assert not controller.unlinkComponent(row, "Input", "/stage/nothing.value")

    assert stage.undo_stack.count() == count
    assert len(target["value"].input_links) == 1


def test_the_x_button_asks_to_unlink(qapp):
    engine = qapp.qml_engine
    component = QtQml.QQmlComponent(
        engine, QtCore.QUrl.fromLocalFile(str(LINK_DELEGATE_QML))
    )
    item = component.create()
    assert item is not None, component.errorString()
    try:
        item.setProperty("linkDirection", "Input")
        item.setProperty("linkPath", "/stage/source.value")
        button = item.findChild(QtCore.QObject, "unlinkButton")
        assert button is not None
        spy = QtTest.QSignalSpy(item, QtCore.SIGNAL("unlinkRequested()"))

        QtCore.QMetaObject.invokeMethod(button, "click")

        assert spy.count() == 1
    finally:
        item.deleteLater()


def find_items(item, object_name):
    """Find the items called `object_name` below an item, delegates included."""
    found = [item] if item.objectName() == object_name else []
    for child in item.childItems():
        found.extend(find_items(child, object_name))
    return found


def test_clicking_the_x_button_in_the_inspector_removes_the_link(linked, qtbot):
    controller, _row, _source, target, _stage = linked
    qtbot.waitUntil(
        lambda: bool(find_items(controller.view_root, "unlinkButton")), timeout=3000
    )
    (button,) = find_items(controller.view_root, "unlinkButton")

    QtCore.QMetaObject.invokeMethod(button, "click")

    assert target["value"].input_links == []


def test_the_x_button_is_at_the_right_end_of_the_item(qapp):
    engine = qapp.qml_engine
    component = QtQml.QQmlComponent(
        engine, QtCore.QUrl.fromLocalFile(str(LINK_DELEGATE_QML))
    )
    item = component.create()
    assert item is not None, component.errorString()
    try:
        item.setProperty("linkPath", "/stage/source.value")
        for width in (300.0, 640.0):
            item.setProperty("width", width)
            button = item.findChild(QtCore.QObject, "unlinkButton")

            right_edge = button.mapToItem(item, QtCore.QPointF(button.width(), 0)).x()

            assert right_edge == pytest.approx(
                width - item.property("rightPadding"), abs=1.0
            )
    finally:
        item.deleteLater()


def test_in_the_inspector_the_row_keeps_its_height_and_the_x_is_at_its_right(
    linked, qtbot
):
    controller, *_ = linked
    qtbot.waitUntil(
        lambda: bool(find_items(controller.view_root, "unlinkButton")), timeout=3000
    )
    (button,) = find_items(controller.view_root, "unlinkButton")
    delegate = button.parentItem().parentItem()

    assert delegate.height() == pytest.approx(30)
    right_edge = button.mapToItem(delegate, QtCore.QPointF(button.width(), 0)).x()
    assert right_edge == pytest.approx(
        delegate.width() - delegate.property("rightPadding"), abs=1.0
    )
    assert delegate.width() > 100
