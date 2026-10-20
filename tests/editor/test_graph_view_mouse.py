import warnings

import pytest
from PySide6 import QtCore, QtTest

LEFT = QtCore.Qt.MouseButton.LeftButton
MIDDLE = QtCore.Qt.MouseButton.MiddleButton
NO_MODIFIER = QtCore.Qt.KeyboardModifier.NoModifier
CONTROL = QtCore.Qt.KeyboardModifier.ControlModifier


@pytest.fixture
def shown_view(stage_editor, qtbot):
    stage_editor.show()
    qtbot.waitExposed(stage_editor)
    view = stage_editor.gr_view
    view.resize(600, 400)
    view.centerOn(0, 0)
    return view


@pytest.fixture(autouse=True)
def deprecations_are_errors():
    """Mouse handling must not use the deprecated QMouseEvent accessors."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error", category=DeprecationWarning, message=".*QMouseEvent.*"
        )
        yield


def empty_spot(view) -> QtCore.QPoint:
    return view.mapFromScene(QtCore.QPointF(150, 100))


def test_ctrl_press_on_the_background_starts_a_cut(shown_view):
    view = shown_view
    spot = empty_spot(view)

    QtTest.QTest.mousePress(view.viewport(), LEFT, CONTROL, spot)
    assert view.interaction_mode is view.InteractionMode.LINK_CUT

    QtTest.QTest.mouseRelease(view.viewport(), LEFT, CONTROL, spot)
    assert view.interaction_mode is view.InteractionMode.NOOP


def test_cutline_follows_the_mouse_while_cutting(shown_view):
    view = shown_view
    start = empty_spot(view)
    end = start + QtCore.QPoint(80, 40)

    QtTest.QTest.mousePress(view.viewport(), LEFT, CONTROL, start)
    QtTest.QTest.mouseMove(view.viewport(), end)

    assert len(view.cutline.line_points) >= 1
    assert view.last_scene_mouse_pos == view.mapToScene(end)
    QtTest.QTest.mouseRelease(view.viewport(), LEFT, CONTROL, end)


def test_middle_button_pans_and_restores_selection_mode(shown_view):
    view = shown_view
    spot = empty_spot(view)

    QtTest.QTest.mousePress(view.viewport(), MIDDLE, NO_MODIFIER, spot)
    assert view.is_dragging  # not interactive while panning
    assert view.dragMode() == view.DragMode.ScrollHandDrag

    QtTest.QTest.mouseRelease(view.viewport(), MIDDLE, NO_MODIFIER, spot)
    assert not view.is_dragging
    assert view.dragMode() == view.DragMode.RubberBandDrag


def test_left_press_remembers_where_it_was_in_the_scene(shown_view):
    view = shown_view
    spot = empty_spot(view)

    QtTest.QTest.mousePress(view.viewport(), LEFT, NO_MODIFIER, spot)
    QtTest.QTest.mouseRelease(view.viewport(), LEFT, NO_MODIFIER, spot)

    assert view.last_lmb_click_pos == view.mapToScene(spot)
