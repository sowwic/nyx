import pytest
from PySide6 import QtCore, QtGui

from nyx.api.v1 import CoreNodes
from nyx.editor.views.stage_graph_debug_overlay import StageGraphDebugOverlay


@pytest.fixture(autouse=True)
def restore_overlay_config(main_window):
    """The config outlives a test, so the toggle must not leak into the next one."""
    yield
    main_window.config.values.editor_widgets.graphics_stage.viewport_debug_overlay = (
        False
    )


@pytest.fixture
def overlay(stage_editor):
    overlay = StageGraphDebugOverlay()
    overlay.attach(stage_editor.gr_view)
    yield overlay
    overlay.attach(None)


def test_paint_rate_counts_the_last_second_only():
    overlay = StageGraphDebugOverlay()
    overlay.record_paint(0.01, now=0.0)
    overlay.record_paint(0.01, now=9.5)
    overlay.record_paint(0.01, now=9.9)

    assert overlay.paint_rate(now=10.0) == 2
    assert overlay.paint_rate(now=20.0) == 0


def test_paint_times_report_last_and_average():
    overlay = StageGraphDebugOverlay()
    overlay.record_paint(0.004, now=9.5)
    overlay.record_paint(0.008, now=9.9)

    last, average = overlay.paint_times(now=10.0)

    assert last == pytest.approx(8.0)
    assert average == pytest.approx(6.0)


def test_paint_times_are_zero_while_idle():
    overlay = StageGraphDebugOverlay()
    overlay.record_paint(0.004, now=0.0)

    assert overlay.paint_times(now=10.0) == (0.0, 0.0)


def test_lines_describe_the_view(stage_editor, create_node, overlay):
    create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)

    text = "\n".join(overlay.lines())

    for label in ("paints/s", "zoom", "detail", "nodes", "links", "plugs", "animated"):
        assert label in text
    assert "scale 100%" in text
    assert "FULL" in text


def test_detail_follows_the_zoom(stage_editor, overlay):
    stage_editor.gr_view.setTransform(QtGui.QTransform.fromScale(0.1, 0.1))

    assert any("MINIMAL" in line for line in overlay.lines())


def overlay_config(main_window):
    return main_window.config.values.editor_widgets.graphics_stage


def test_view_menu_toggle_sets_config_and_attaches_the_overlay(
    main_window, stage_editor
):
    action = main_window.menubar_view_menu.debug_overlay_action
    overlay = main_window.viewport_debug_overlay
    assert action.text() == "Viewport Debug Overlay"
    assert not action.isChecked()
    assert overlay.view is None
    assert stage_editor.gr_view.debug_overlay is None

    action.setChecked(True)

    assert overlay_config(main_window).viewport_debug_overlay
    assert overlay.view is stage_editor.gr_view
    assert stage_editor.gr_view.debug_overlay is overlay

    action.setChecked(False)

    assert not overlay_config(main_window).viewport_debug_overlay
    assert overlay.view is None
    assert stage_editor.gr_view.debug_overlay is None


def test_view_menu_is_in_the_menubar(main_window):
    titles = [action.text() for action in main_window.menuBar().actions()]

    assert "&View" in titles


def test_overlay_toggle_has_the_f3_shortcut(main_window):
    action = main_window.menubar_view_menu.debug_overlay_action

    assert action.shortcut() == QtGui.QKeySequence(QtCore.Qt.Key.Key_F3)


def test_overlay_follows_the_active_window(main_window, stage_editor):
    first = stage_editor
    main_window.menubar_view_menu.debug_overlay_action.setChecked(True)
    overlay = main_window.viewport_debug_overlay

    main_window.on_stage_new()
    second = main_window.current_stage_graph

    assert second is not first
    assert overlay.view is second.gr_view
    assert second.gr_view.debug_overlay is overlay
    assert first.gr_view.debug_overlay is None

    first_window = next(
        window
        for window in main_window.mdi_area.subWindowList()
        if window.widget() is first
    )
    main_window.activate_editor_window(first_window)

    assert overlay.view is first.gr_view
    assert second.gr_view.debug_overlay is None


def test_overlay_survives_its_view_being_closed(main_window, stage_editor):
    main_window.menubar_view_menu.debug_overlay_action.setChecked(True)
    overlay = main_window.viewport_debug_overlay

    main_window.mdi_area.currentSubWindow().close()

    assert overlay.view is None


def test_applying_the_config_attaches_the_overlay(main_window, stage_editor):
    overlay_config(main_window).viewport_debug_overlay = True

    main_window.apply_config_values()

    assert main_window.menubar_view_menu.debug_overlay_action.isChecked()
    assert main_window.viewport_debug_overlay.view is stage_editor.gr_view


def test_attaching_forgets_the_paints_of_the_previous_view(overlay, stage_editor):
    overlay.record_paint(0.01, now=1.0)

    overlay.attach(None)
    overlay.attach(stage_editor.gr_view)

    assert overlay.paint_rate(now=1.0) == 0


def test_detached_overlay_has_nothing_to_show():
    assert StageGraphDebugOverlay().lines() == []


def test_overlay_is_drawn_over_the_viewport_and_counts_paints(stage_editor, overlay):
    view = stage_editor.gr_view
    view.resize(400, 300)

    image = view.grab().toImage()

    # The corner holds the dark box of the overlay, not the plain background.
    corner = image.pixelColor(14, 14)
    assert corner != view.backgroundBrush().color()
    assert overlay.paint_rate() >= 1


def test_view_without_the_overlay_does_not_count_paints(stage_editor, overlay):
    overlay.attach(None)

    stage_editor.gr_view.grab()

    assert overlay.paint_rate() == 0


def animated_line(overlay) -> str:
    return next(line for line in overlay.lines() if line.startswith("animated"))


def test_animated_line_counts_active_and_skipped_links(
    stage_editor, create_node, overlay
):
    from nyx.api.v1 import commands

    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )
    view = stage_editor.gr_view
    animator = stage_editor.gr_stage.link_animator
    assert animator.is_running

    view.setTransform(QtGui.QTransform.fromScale(1.0, 1.0))
    if view.isVisible():
        assert animated_line(overlay).split()[1:] == ["1", "(0", "skipped)"]

    # Too small to see: the timer runs, the pulse is skipped.
    view.setTransform(QtGui.QTransform.fromScale(0.1, 0.1))
    assert animator.is_running
    assert animated_line(overlay).split()[1:] == ["0", "(1", "skipped)"]


def test_links_outside_of_the_view_count_as_skipped(stage_editor, create_node, overlay):
    from nyx.api.v1 import commands

    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )

    for gr_node in stage_editor.gr_stage.gr_nodes():
        gr_node.setPos(100000, 100000)

    assert animated_line(overlay).split()[1:] == ["0", "(1", "skipped)"]


def test_animated_line_without_animations(overlay):
    assert animated_line(overlay).split()[1:] == ["0", "(0", "skipped)"]
