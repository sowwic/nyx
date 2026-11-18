import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreNodes, Stage
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.editor.views.nodes_palette_view import NodesPaletteView
from nyx.editor.widgets.dialogs.stage_object_picker import StageObjectPickerDialog
from nyx.editor.widgets.output_log.output_log_widget import OutputLogWidget
from nyx.utils import pyside_fn
from stage_helpers import STAGES


def search_icon_image() -> QtGui.QImage:
    return QtGui.QIcon(":/icons/search").pixmap(24, 24).toImage()


def leading_search_actions(line_edit: QtWidgets.QLineEdit) -> list[QtGui.QAction]:
    return [
        action
        for action in line_edit.actions()
        if action.icon().pixmap(24, 24).toImage() == search_icon_image()
    ]


def test_the_search_icon_resource_exists():
    assert not QtGui.QIcon(":/icons/search").isNull()


def test_add_search_icon_puts_the_icon_in_front_of_the_text(qtbot):
    line_edit = QtWidgets.QLineEdit()
    qtbot.addWidget(line_edit)

    action = pyside_fn.add_search_icon(line_edit)

    assert action in line_edit.actions()
    assert not action.icon().isNull()
    assert leading_search_actions(line_edit) == [action]


def test_the_log_search_field_has_the_icon(qtbot):
    widget = OutputLogWidget()
    qtbot.addWidget(widget)

    assert len(leading_search_actions(widget._filter_bar._search_field)) == 1


def test_the_stage_object_picker_search_field_has_the_icon(qtbot):
    stage = Stage()
    STAGES.append(stage)
    dialog = StageObjectPickerDialog(stage)
    qtbot.addWidget(dialog)

    assert len(leading_search_actions(dialog.search_field)) == 1


def qml_root(view, qtbot):
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    return view.rootObject()


def test_the_nodes_palette_search_bar_has_the_icon(qtbot):
    view = NodesPaletteView(drag_enabled=True)
    qtbot.addWidget(view)
    view.show()
    root = qml_root(view, qtbot)

    icon = root.findChild(QtCore.QObject, "searchBar").findChild(
        QtCore.QObject, "searchIcon"
    )

    assert icon is not None
    assert icon.property("visible")
    assert icon.property("width") > 0


def test_the_components_search_field_has_the_icon_and_leaves_room_for_it(
    main_window, stage_editor, create_node, qtbot
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.BRANCH)
    main_window.panel_manager.set_open("inspector", True)
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    root = qml_root(view, qtbot)

    field = root.findChild(QtCore.QObject, "componentsSearchField")
    icon = field.findChild(QtCore.QObject, "searchIcon")

    assert icon is not None
    assert field.property("leftPadding") >= icon.property("x") + icon.property("width")


@pytest.fixture(autouse=True)
def _close_inspector(main_window):
    yield
    main_window.panel_manager.set_open("inspector", False)
