import pytest
from PySide6 import QtCore, QtTest

from nyx.editor.views.stage_graph_view import StageGraphView

RUBBER_BAND = StageGraphView.InteractionMode.RUBBER_BAND
NOOP = StageGraphView.InteractionMode.NOOP


@pytest.fixture
def three_nodes(stage_editor, create_node):
    stage = stage_editor.stage
    nodes = [create_node(stage, name) for name in ("a", "b", "c")]
    for index, node in enumerate(nodes):
        node.set_position(QtCore.QPointF(index * 250, 0))
    stage_editor.gr_stage.rebuild_current_scope()
    return stage_editor, nodes


@pytest.fixture
def selection_changes(three_nodes):
    """Selections the selection model reported, one list of names per signal."""
    editor, _nodes = three_nodes
    seen = []
    editor.selection_model.selectionChanged.connect(
        lambda *_: seen.append(sorted(n.name for n in editor.list_selected_nodes()))
    )
    return seen


# ======== Stage ========= #


def test_scene_selection_is_not_synced_while_a_band_is_dragged(
    three_nodes, selection_changes
):
    editor, nodes = three_nodes
    gr_stage = editor.gr_stage
    editor.gr_view.set_interaction_mode(RUBBER_BAND)

    for node in nodes:
        gr_stage.get_gr_node(node).setSelected(True)

    assert editor.gr_view.is_rubber_banding
    assert selection_changes == []
    assert editor.list_selected_nodes() == []


def test_releasing_the_band_syncs_the_selection_once(three_nodes, selection_changes):
    editor, nodes = three_nodes
    gr_stage = editor.gr_stage
    editor.gr_view.set_interaction_mode(RUBBER_BAND)
    for node in nodes:
        gr_stage.get_gr_node(node).setSelected(True)

    editor.gr_view.set_interaction_mode(NOOP)
    gr_stage.on_selection_changed()

    assert not editor.gr_view.is_rubber_banding
    assert sorted(n.name for n in editor.list_selected_nodes()) == ["a", "b", "c"]
    assert selection_changes == [["a", "b", "c"]]  # one report for all the nodes


def test_a_band_that_picks_nothing_clears_the_selection(three_nodes, selection_changes):
    editor, nodes = three_nodes
    gr_stage = editor.gr_stage
    gr_stage.get_gr_node(nodes[0]).setSelected(True)
    assert [n.name for n in editor.list_selected_nodes()] == ["a"]
    selection_changes.clear()

    editor.gr_view.set_interaction_mode(RUBBER_BAND)
    gr_stage.clearSelection()
    assert [n.name for n in editor.list_selected_nodes()] == ["a"]  # not yet
    editor.gr_view.set_interaction_mode(NOOP)
    gr_stage.on_selection_changed()

    assert editor.list_selected_nodes() == []
    assert selection_changes == [[]]


def test_selection_outside_of_a_band_is_synced_at_once(three_nodes, selection_changes):
    editor, nodes = three_nodes

    editor.gr_stage.get_gr_node(nodes[0]).setSelected(True)

    assert [n.name for n in editor.list_selected_nodes()] == ["a"]
    assert selection_changes


# ======== Inspector ========= #


def test_inspector_waits_for_the_end_of_the_band(main_window, three_nodes, monkeypatch):
    editor, nodes = three_nodes
    calls = []
    monkeypatch.setattr(
        main_window.inspector, "update_data", lambda *a: calls.append(1), raising=True
    )
    editor.selection_model.selectionChanged.disconnect()
    editor.selection_model.selectionChanged.connect(
        editor.gr_stage.on_selection_model_selection_changed
    )
    editor.selection_model.selectionChanged.connect(
        lambda *_: main_window.inspector.update_data()
    )
    gr_stage = editor.gr_stage
    editor.gr_view.set_interaction_mode(RUBBER_BAND)
    # Turning undo off for the band refreshes the inspector once, that is not the
    # selection.
    calls.clear()

    for node in nodes:
        gr_stage.get_gr_node(node).setSelected(True)
    assert calls == []

    editor.gr_view.set_interaction_mode(NOOP)
    calls.clear()
    gr_stage.on_selection_changed()

    assert len(calls) == 1  # one update for all the nodes of the band


# ======== View ========= #


def drag_band(view, start: QtCore.QPoint, end: QtCore.QPoint, steps=6):
    viewport = view.viewport()
    QtTest.QTest.mousePress(
        viewport,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        start,
    )
    yield "pressed"
    for step in range(1, steps + 1):
        point = start + (end - start) * step / steps
        QtTest.QTest.mouseMove(viewport, point)
        yield "moved"
    QtTest.QTest.mouseRelease(
        viewport,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        end,
    )
    yield "released"


def test_view_is_in_band_mode_from_press_to_release(three_nodes, qtbot):
    editor, _nodes = three_nodes
    view = editor.gr_view
    editor.show()
    qtbot.waitExposed(editor)
    view.resize(900, 400)
    view.centerOn(250, 50)
    start = view.mapFromScene(QtCore.QPointF(-200, -150))
    end = view.mapFromScene(QtCore.QPointF(700, 250))
    band = view.InteractionMode.RUBBER_BAND

    modes = []
    for _stage in drag_band(view, start, end):
        modes.append((view.interaction_mode, editor.gr_view.is_rubber_banding))

    assert all(mode is band and active for mode, active in modes[:-1])
    assert modes[-1] == (view.InteractionMode.NOOP, False)


def test_view_reports_the_band_mode(three_nodes):
    editor, _nodes = three_nodes
    view = editor.gr_view

    view.set_interaction_mode(view.InteractionMode.RUBBER_BAND)
    assert editor.gr_view.is_rubber_banding

    view.set_interaction_mode(view.InteractionMode.NOOP)
    assert not editor.gr_view.is_rubber_banding


def test_other_modes_do_not_hold_back_the_selection(three_nodes):
    editor, _nodes = three_nodes
    view = editor.gr_view

    for mode in (view.InteractionMode.LINK_DRAG, view.InteractionMode.LINK_CUT):
        view.set_interaction_mode(mode)
        assert not editor.gr_view.is_rubber_banding
    view.set_interaction_mode(view.InteractionMode.NOOP)


def test_the_view_is_busy_while_a_band_is_dragged(three_nodes):
    editor, _nodes = three_nodes
    view = editor.gr_view
    states = []
    view.state_changed.connect(lambda: states.append(view.is_idle))

    view.set_interaction_mode(view.InteractionMode.RUBBER_BAND)
    assert not view.is_idle
    assert not view.idle_condition()

    view.set_interaction_mode(view.InteractionMode.NOOP)
    assert view.is_idle
    assert states == [False, True]


def test_dragging_a_band_over_nodes_syncs_only_at_the_end(
    three_nodes, selection_changes, qtbot
):
    editor, _nodes = three_nodes
    view = editor.gr_view
    editor.show()
    qtbot.waitExposed(editor)
    view.resize(900, 400)
    view.centerOn(250, 50)
    start = view.mapFromScene(QtCore.QPointF(-200, -150))
    end = view.mapFromScene(QtCore.QPointF(700, 250))
    during = []

    for stage in drag_band(view, start, end):
        if stage == "moved":
            during.append(len(selection_changes))

    assert sorted(n.name for n in editor.list_selected_nodes()) == ["a", "b", "c"]
    # Nothing was reported while dragging, whatever the band had picked up.
    assert len(set(during)) == 1
    assert selection_changes[-1] == ["a", "b", "c"]


def test_a_new_press_ends_a_band_that_was_never_released(three_nodes, qtbot):
    editor, nodes = three_nodes
    gr_stage = editor.gr_stage
    view = editor.gr_view
    view.set_interaction_mode(view.InteractionMode.RUBBER_BAND)
    editor.show()
    qtbot.waitExposed(editor)
    gr_node = gr_stage.get_gr_node(nodes[0])
    center = view.mapFromScene(gr_node.sceneBoundingRect().center())

    QtTest.QTest.mouseClick(
        view.viewport(),
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        center,
    )

    assert view.interaction_mode is view.InteractionMode.NOOP
    assert not editor.gr_view.is_rubber_banding
    assert [n.name for n in editor.list_selected_nodes()] == ["a"]


def test_the_band_rectangle_is_gone_after_the_release(three_nodes, qtbot):
    editor, _nodes = three_nodes
    view = editor.gr_view
    editor.show()
    qtbot.waitExposed(editor)
    view.resize(900, 400)
    view.centerOn(250, 50)
    start = view.mapFromScene(QtCore.QPointF(-200, -150))
    end = view.mapFromScene(QtCore.QPointF(700, 250))
    rects = []
    view.rubberBandChanged.connect(lambda rect, *_: rects.append(rect))

    stages = []
    for stage in drag_band(view, start, end):
        stages.append(stage)
        if stage == "moved":
            assert not view.rubberBandRect().isNull()  # the band is drawn while dragging

    # No mouse move after the release.
    assert view.rubberBandRect().isNull()
    assert rects[-1].isNull()
