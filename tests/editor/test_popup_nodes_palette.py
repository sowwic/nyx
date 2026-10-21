from unittest import mock

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette


@pytest.fixture
def no_exec(monkeypatch):
    """Replace the blocking `exec` with a recorder capturing the dialog."""
    captured = []

    def fake_exec(self):
        captured.append(self)
        return 0

    monkeypatch.setattr(PopupNodesPalette, "exec", fake_exec)
    return captured


def test_popup_centered_without_stage_graph_does_nothing(main_window, no_exec):
    assert PopupNodesPalette.popup_centered() is None
    assert no_exec == []


def test_popup_centered_is_centered_over_window(stage_editor, main_window, no_exec):
    palette = PopupNodesPalette.popup_centered()
    assert no_exec == [palette]
    assert palette.parent() is main_window
    center = main_window.geometry().center()
    screen = (
        QtGui.QGuiApplication.screenAt(center) or QtGui.QGuiApplication.primaryScreen()
    )
    # Centered, unless that would put it out of the screen
    expected = PopupNodesPalette.clamp_to_bounds(
        center - palette.rect().center(), palette.size(), screen.availableGeometry()
    )
    assert palette.pos() == expected


def test_popup_centered_stays_inside_screen(stage_editor, main_window, no_exec):
    palette = PopupNodesPalette.popup_centered()
    screen = QtGui.QGuiApplication.screenAt(main_window.geometry().center())
    available = (screen or QtGui.QGuiApplication.primaryScreen()).availableGeometry()
    assert available.contains(palette.pos())


def test_popup_at_cursor_is_moved_inside_screen(stage_editor, no_exec, monkeypatch):
    screen = QtGui.QGuiApplication.primaryScreen()
    available = screen.availableGeometry()
    corner = available.bottomRight()
    monkeypatch.setattr(QtGui.QCursor, "pos", staticmethod(lambda: corner))

    palette = PopupNodesPalette.popup()
    assert available.contains(palette.geometry().bottomRight()) or (
        palette.width() > available.width() or palette.height() > available.height()
    )
    assert palette.geometry().topLeft() == PopupNodesPalette.clamp_to_bounds(
        corner, palette.size(), available
    )


@pytest.mark.parametrize(
    "top_left, expected",
    [
        ((50, 60), (50, 60)),  # fits
        ((900, 60), (600, 60)),  # past the right edge
        ((50, 700), (50, 400)),  # past the bottom edge
        ((-30, -40), (0, 0)),  # past the top left
        ((900, 700), (600, 400)),  # past the bottom right
    ],
)
def test_clamp_to_bounds_keeps_rect_inside(top_left, expected):
    bounds = QtCore.QRect(0, 0, 1000, 900)
    result = PopupNodesPalette.clamp_to_bounds(
        QtCore.QPoint(*top_left), QtCore.QSize(400, 500), bounds
    )
    assert (result.x(), result.y()) == expected


def test_clamp_to_bounds_keeps_top_left_when_rect_is_bigger_than_bounds():
    bounds = QtCore.QRect(100, 50, 300, 300)
    result = PopupNodesPalette.clamp_to_bounds(
        QtCore.QPoint(500, 500), QtCore.QSize(400, 500), bounds
    )
    assert (result.x(), result.y()) == (100, 50)


def test_popup_centered_passes_spawn_position_to_spawner(stage_editor, no_exec):
    position = QtCore.QPointF(33, 44)
    palette = PopupNodesPalette.popup_centered(position)
    assert palette._nodes_palette_view.nodes_spawner.spawn_position == position


def test_palette_is_modal_dialog_with_fixed_size(stage_editor, no_exec):
    palette = PopupNodesPalette.popup_centered()
    assert isinstance(palette, QtWidgets.QDialog)
    assert palette.size() == QtCore.QSize(400, 500)
    assert palette.testAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)


def test_spawned_node_closes_palette(stage_editor, no_exec, qtbot):
    from nyx.api.v1 import CoreNodes

    palette = PopupNodesPalette.popup_centered()
    destroyed = mock.Mock()
    palette.destroyed.connect(destroyed)

    palette._nodes_palette_view.nodes_spawner.spawnNode(CoreNodes.EMPTY)
    qtbot.waitUntil(lambda: destroyed.called, timeout=2000)


def palette_root(view, qtbot):
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=2000)
    return view.rootObject()


def invoke(root, name, *args):
    QtCore.QMetaObject.invokeMethod(
        root,
        name,
        QtCore.Qt.ConnectionType.DirectConnection,
        *[QtCore.Q_ARG("QVariant", arg) for arg in args],
    )


def current_index(root):
    return root.findChild(QtCore.QObject, "nodesPaletteListView").property(
        "currentIndex"
    )


def test_arrow_keys_move_the_selection(stage_editor, qtbot):
    palette = PopupNodesPalette(QtCore.QPointF())
    qtbot.addWidget(palette)
    palette.show()
    root = palette_root(palette._nodes_palette_view, qtbot)

    assert current_index(root) == 0
    invoke(root, "moveSelection", 1)
    invoke(root, "moveSelection", 1)
    assert current_index(root) == 2
    invoke(root, "moveSelection", -1)
    assert current_index(root) == 1
    invoke(root, "moveSelection", -50)
    assert current_index(root) == 0
    invoke(root, "moveSelection", 500)
    assert current_index(root) > 2


def test_enter_creates_the_selected_node(stage_editor, qtbot):
    palette = PopupNodesPalette(QtCore.QPointF())
    qtbot.addWidget(palette)
    palette.show()
    root = palette_root(palette._nodes_palette_view, qtbot)
    invoke(root, "moveSelection", 1)

    with qtbot.waitSignal(palette._nodes_palette_view.nodes_spawner.nodeSpawned):
        invoke(root, "activateSelection")


def test_search_bar_gets_the_focus_when_the_palette_shows(stage_editor, qtbot):
    palette = PopupNodesPalette(QtCore.QPointF())
    qtbot.addWidget(palette)
    palette.show()
    root = palette_root(palette._nodes_palette_view, qtbot)

    search_bar = root.findChild(QtCore.QObject, "searchBar")
    field = search_bar.findChild(QtCore.QObject, "searchField")
    qtbot.waitUntil(lambda: bool(field.property("activeFocus")), timeout=2000)


def test_docked_palette_has_no_keyboard_selection(stage_editor, qtbot):
    from nyx.editor.views.nodes_palette_view import NodesPaletteView

    view = NodesPaletteView(drag_enabled=True)
    qtbot.addWidget(view)
    view.show()
    root = palette_root(view, qtbot)
    spawned = []
    view.nodes_spawner.nodeSpawned.connect(spawned.append)

    assert current_index(root) == -1
    invoke(root, "moveSelection", 1)
    assert current_index(root) == -1
    invoke(root, "activateSelection")
    assert spawned == []


def test_selection_follows_drag_enabled(stage_editor, qtbot):
    from nyx.editor.views.nodes_palette_view import NodesPaletteView

    view = NodesPaletteView(drag_enabled=False)
    qtbot.addWidget(view)
    view.show()
    root = palette_root(view, qtbot)
    assert current_index(root) == 0

    view.drag_enabled = True
    assert current_index(root) == -1
    view.drag_enabled = False
    assert current_index(root) == 0
