import pytest
from PySide6 import QtCore, QtWidgets

from nyx.static.vars import ROOT_NODE_PATH
from nyx.editor.panels import PANEL_REGISTRY, FloatingAnchor, PanelRegistry
from nyx.editor.panels.panel_registry import PanelDefinition


def test_panels_are_registered():
    ids = {definition.panel_id for definition in PANEL_REGISTRY.definitions()}
    assert {"nodes", "tree", "undo", "bridge", "inspector", "console"} <= ids


def test_panel_definitions_register_in_order_into_a_fresh_registry():
    from nyx.editor.panels.panel_definitions import (
        PANELS,
        SIDEBAR_ACTIONS,
        register_panels,
    )

    panel_ids = [definition.panel_id for definition in PANELS]
    button_ids = [definition.button_id for definition in SIDEBAR_ACTIONS]
    assert len(set(panel_ids + button_ids)) == len(panel_ids + button_ids)

    registry = PanelRegistry()
    register_panels(registry)

    assert tuple(registry.definitions()) == PANELS
    assert tuple(registry.action_buttons()) == SIDEBAR_ACTIONS


def test_registry_replaces_by_id():
    registry = PanelRegistry()
    registry.register(PanelDefinition("a", "A", "", lambda window: None))
    registry.register(PanelDefinition("a", "B", "", lambda window: None))
    assert [definition.title for definition in registry.definitions()] == ["B"]
    registry.unregister("a")
    assert registry.get("a") is None


def test_opening_a_panel_does_not_resize_the_graph_area(main_window, manager, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)
    before = main_window.mdi_area.geometry()

    manager.set_open("tree", True)
    manager.set_open("console", True)

    assert main_window.mdi_area.geometry() == before
    panel = manager.panel("tree")
    assert panel.isVisible()
    assert panel.parentWidget() is main_window.panel_host.canvas


def test_sidebar_click_toggles_the_panel(main_window, manager, qtbot):
    button = main_window.panel_sidebar.button("tree")
    qtbot.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    assert manager.is_open("tree")
    assert button.isChecked()

    qtbot.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    assert not manager.is_open("tree")
    assert not button.isChecked()


def test_one_panel_is_open_per_area(manager, main_window):
    manager.set_open("tree", True)
    manager.set_open("nodes", True)
    manager.set_open("inspector", True)

    assert set(manager.open_panel_ids()) == {"nodes", "inspector"}
    assert not main_window.panel_sidebar.button("tree").isChecked()
    assert main_window.panel_sidebar.button("nodes").isChecked()


def test_close_button_closes_the_panel(manager):
    manager.set_open("undo", True)
    manager.panel("undo").close_requested.emit()
    assert not manager.is_open("undo")


def test_panels_are_anchored_to_their_edges(main_window, manager, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)
    for panel_id in ("tree", "inspector", "console"):
        manager.set_open(panel_id, True)
    canvas = main_window.panel_host.canvas

    left, right, bottom = (manager.panel(i) for i in ("tree", "inspector", "console"))
    assert left.geometry().topLeft() == QtCore.QPoint(0, 0)
    assert left.height() == canvas.height()
    assert right.geometry().right() == canvas.width() - 1
    assert bottom.geometry().bottom() == canvas.height() - 1
    assert bottom.x() == left.width()
    assert bottom.geometry().right() == right.x() - 1


def test_every_default_size_is_above_the_minimum_of_its_area():
    from nyx.editor.panels import PanelArea
    from nyx.editor.panels.panel_host import PanelHost

    for area in PanelArea:
        assert PanelHost.DEFAULT_SIZES[area] > PanelHost.MINIMUM_SIZES[area]
    # The side panels are the ones that need room for their content
    assert PanelHost.MINIMUM_SIZES[PanelArea.LEFT] >= 280
    assert PanelHost.MINIMUM_SIZES[PanelArea.RIGHT] >= 280


@pytest.mark.parametrize(
    ("panel_id", "expected_minimum"),
    [("tree", 280), ("inspector", 300), ("console", 180)],
)
def test_a_panel_cannot_be_made_smaller_than_the_minimum_of_its_area(
    main_window, manager, qtbot, panel_id, expected_minimum
):
    main_window.show()
    qtbot.waitExposed(main_window)
    manager.set_open(panel_id, True)
    panel = manager.panel(panel_id)
    host = main_window.panel_host

    panel.size_requested.emit(20)  # what dragging the grip far inwards asks for

    assert host.panel_size(panel) == expected_minimum
    size = panel.height() if panel_id == "console" else panel.width()
    assert size == expected_minimum


def test_dragging_the_grip_resizes_the_panel(main_window, manager, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)
    manager.set_open("tree", True)
    panel = manager.panel("tree")

    panel.size_requested.emit(400)

    assert panel.width() == 400


def test_sidebar_hides_and_shows_buttons(main_window):
    sidebar = main_window.panel_sidebar
    try:
        sidebar._set_button_visible("bridge", False)
        assert "bridge" not in sidebar.visible_button_ids()
        assert sidebar.hidden_button_ids() == ["bridge"]
        sidebar.set_hidden_buttons(None)
        assert "bridge" in sidebar.visible_button_ids()
    finally:
        sidebar.set_hidden_buttons(None)


def test_config_round_trip(main_window, manager):
    config = main_window.config
    sidebar = main_window.panel_sidebar
    try:
        sidebar._set_button_visible("bridge", False)
        manager.set_open("tree", True)
        main_window.panel_host.set_panel_size(manager.panel("tree"), 411)
        manager.save_config_values(config)
        saved = config.values.main_window.panels
        assert "bridge" in saved.hidden_buttons
        assert saved.open_panels == ["tree"]
        assert saved.sizes["tree"] == 411

        manager.set_open("tree", False)
        sidebar.set_hidden_buttons(None)
        manager.apply_config_values(config)
        assert manager.is_open("tree")
        assert "bridge" not in sidebar.visible_button_ids()
        assert main_window.panel_host.panel_size(manager.panel("tree")) == 411
    finally:
        sidebar.set_hidden_buttons(None)
        config.values.main_window.panels.open_panels = []
        config.values.main_window.panels.hidden_buttons = None
        config.values.main_window.panels.sizes = {}


def test_unknown_panel_id_is_ignored(manager):
    manager.set_open("does-not-exist", True)
    assert manager.panel("does-not-exist") is None


def test_panels_start_below_the_tab_bar(main_window, manager, stage_editor, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)
    manager.set_open("tree", True)
    manager.set_open("inspector", True)
    host = main_window.panel_host
    qtbot.waitUntil(lambda: host.top_inset() > 0, timeout=3000)

    for panel_id in ("tree", "inspector"):
        panel = manager.panel(panel_id)
        assert panel.y() == host.top_inset()
        assert panel.geometry().bottom() == host.canvas.height() - 1


def test_stage_controls_overlay_inspector_button_toggles_and_stays_visible(
    main_window, manager, qtbot
):
    main_window.show()
    qtbot.waitExposed(main_window)
    overlay = main_window.stage_controls_overlay
    assert overlay.inspector_button.isVisible()

    qtbot.mouseClick(overlay.inspector_button, QtCore.Qt.MouseButton.LeftButton)
    assert manager.is_open("inspector")
    assert overlay.inspector_button.isVisible()
    assert overlay.inspector_button.isChecked()

    qtbot.mouseClick(overlay.inspector_button, QtCore.Qt.MouseButton.LeftButton)
    assert not manager.is_open("inspector")


def test_stage_controls_overlay_follows_the_right_panel_then_stops_at_the_left_one(
    main_window, manager, qtbot
):
    main_window.show()
    qtbot.waitExposed(main_window)
    host = main_window.panel_host
    overlay = main_window.stage_controls_overlay
    margin = host.FLOATING_MARGIN
    canvas_width = host.canvas.width()

    assert overlay.geometry().right() == canvas_width - margin - 1

    manager.set_open("inspector", True)
    right = manager.panel("inspector")
    assert overlay.geometry().right() == right.x() - margin - 1

    manager.set_open("tree", True)
    left = manager.panel("tree")
    host.set_panel_size(right, canvas_width)  # wider than the free space
    assert overlay.x() == left.width() + margin
    assert overlay.geometry().intersects(right.geometry())


def test_stage_controls_overlay_orders_run_scope_and_inspector_toggle(main_window):
    overlay = main_window.stage_controls_overlay
    layout = overlay.layout()
    assert [layout.itemAt(i).widget() for i in range(layout.count())] == [
        overlay.run_button,
        overlay.scope_widget,
        overlay.inspector_button,
    ]


def test_scope_widget_follows_the_active_editor(main_window, stage_editor, qtbot):
    scope_widget = main_window.stage_controls_overlay.scope_widget
    assert scope_widget.graph_editor is stage_editor
    assert scope_widget.isEnabled()

    stage_editor.scope_root()
    assert scope_widget.path_line_edit.text() == ROOT_NODE_PATH.as_posix()

    second_editor = main_window.current_stage_graph
    main_window.on_stage_new()
    assert scope_widget.graph_editor is main_window.current_stage_graph
    assert scope_widget.graph_editor is not second_editor


def test_scope_widget_is_disabled_without_an_editor(main_window):
    scope_widget = main_window.stage_controls_overlay.scope_widget
    main_window.on_node_graph_window_activated(None)
    assert scope_widget.graph_editor is None
    assert not scope_widget.isEnabled()
    assert scope_widget.path_line_edit.text() == ""


def test_panel_contents_do_not_show_through_while_their_panel_is_closed(
    main_window, manager, qtbot
):
    main_window.show()
    qtbot.waitExposed(main_window)
    contents = (
        main_window.stage_tree_view,
        main_window.inspector,
        main_window.nodes_palette_view,
        main_window.bridge_panel,
        main_window.undo_view,
        main_window.output_log_widget,
    )
    for content in contents:
        if content.parentWidget() is main_window:
            assert not content.isVisible()


def test_settings_button_triggers_the_config_action_when_clicked(main_window, qtbot):
    from unittest import mock

    from nyx.editor.core.action_registry import ACTION_REGISTRY

    button = main_window.panel_sidebar.button("settings")
    assert button is not None
    assert not button.isCheckable()
    handler = mock.Mock()
    action = ACTION_REGISTRY.action("edit.edit_config")
    action.triggered.connect(handler)
    try:
        qtbot.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    finally:
        action.triggered.disconnect(handler)
    handler.assert_called_once()


def test_help_button_opens_a_menu_with_the_help_actions(main_window):
    from nyx.editor.core.action_registry import ACTION_REGISTRY
    from nyx.editor.core.actions import ActionId

    button = main_window.panel_sidebar.button("help")

    assert not button.isCheckable()
    assert button.popupMode() == QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
    assert button.menu().actions() == [
        ACTION_REGISTRY.action(ActionId.DOCUMENTATION),
        ACTION_REGISTRY.action(ActionId.SUBMIT_ISSUE),
        ACTION_REGISTRY.action(ActionId.ABOUT),
    ]
    assert button.text() == "Help"
    assert not button.icon().isNull()


def test_right_clicking_the_settings_button_lists_the_config_actions(main_window):
    from nyx.editor.core.action_registry import ACTION_REGISTRY
    from nyx.editor.core.actions import ActionId

    button = main_window.panel_sidebar.button("settings")

    assert button.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.ActionsContextMenu
    assert button.actions() == [
        ACTION_REGISTRY.action(ActionId.RESET_CONFIG),
    ]
    assert button.menu() is None


def test_action_buttons_are_in_the_bottom_group_after_the_console_button(main_window):
    sidebar = main_window.panel_sidebar
    console_y = sidebar.button("console").y()
    assert console_y < sidebar.button("help").y() < sidebar.button("settings").y()


def test_persistent_buttons_are_at_the_bottom_and_the_others_at_the_top(main_window):
    sidebar = main_window.panel_sidebar
    persistent = {"console", "help", "settings"}
    others = {"nodes", "tree", "undo", "bridge"}
    for button_id in persistent:
        assert sidebar.is_persistent(button_id)
    for button_id in others:
        assert not sidebar.is_persistent(button_id)
    lowest_other = max(sidebar.button(i).y() for i in others)
    assert lowest_other < min(sidebar.button(i).y() for i in persistent)


def test_persistent_buttons_cannot_be_hidden(main_window):
    sidebar = main_window.panel_sidebar
    try:
        sidebar._set_button_visible("settings", False)
        sidebar.set_hidden_buttons(["console", "help", "settings", "bridge"])
        assert sidebar.hidden_button_ids() == ["bridge"]
        assert {"console", "help", "settings"} <= set(sidebar.visible_button_ids())

        menu = sidebar._create_context_menu()
        offered = [
            action.text() for action in menu.actions() if not action.isSeparator()
        ]
        assert "Bridge" in offered
        assert not {"Console", "Docs", "Settings"} & set(offered)
    finally:
        sidebar.set_hidden_buttons(None)


def test_a_button_added_later_is_not_hidden_by_a_saved_list(main_window):
    sidebar = main_window.panel_sidebar
    try:
        sidebar.set_hidden_buttons(["bridge"])  # list saved before help existed
        assert "bridge" not in sidebar.visible_button_ids()
        assert {"help", "settings", "console", "tree"} <= set(
            sidebar.visible_button_ids()
        )
    finally:
        sidebar.set_hidden_buttons(None)


# ---- Floating widgets ----
@pytest.fixture
def floating(main_window, manager, qtbot):
    """Add fixed size stand-ins to the panel host. Returns the factory."""
    main_window.show()
    qtbot.waitExposed(main_window)
    host = main_window.panel_host
    added = []

    def add(anchor, width=100, height=40):
        label = QtWidgets.QLabel("floating")
        label.setFixedSize(width, height)
        host.add_floating_widget(label, anchor)
        added.append(label)
        return label

    yield add
    for label in added:
        host.remove_floating_widget(label)
        label.deleteLater()


def test_floating_widgets_sit_in_their_corners(main_window, floating):
    host = main_window.panel_host
    canvas = host.canvas
    margin, top = host.FLOATING_MARGIN, host.top_inset()

    top_left = floating(FloatingAnchor.TOP_LEFT)
    bottom_left = floating(FloatingAnchor.BOTTOM_LEFT)
    bottom_right = floating(FloatingAnchor.BOTTOM_RIGHT)

    assert top_left.pos() == QtCore.QPoint(margin, top + margin)
    assert bottom_left.pos() == QtCore.QPoint(
        margin, canvas.height() - margin - bottom_left.height()
    )
    assert bottom_right.geometry().right() == canvas.width() - margin - 1
    assert bottom_right.geometry().bottom() == canvas.height() - margin - 1


def test_widgets_in_the_same_top_corner_stack_downwards(main_window, floating):
    host = main_window.panel_host
    first = floating(FloatingAnchor.TOP_LEFT)
    second = floating(FloatingAnchor.TOP_LEFT, height=60)
    third = floating(FloatingAnchor.TOP_LEFT)

    assert second.y() == first.geometry().bottom() + 1 + host.FLOATING_SPACING
    assert third.y() == second.geometry().bottom() + 1 + host.FLOATING_SPACING
    assert first.x() == second.x() == third.x()


def test_widgets_in_the_same_bottom_corner_stack_upwards(main_window, floating):
    host = main_window.panel_host
    first = floating(FloatingAnchor.BOTTOM_LEFT)
    second = floating(FloatingAnchor.BOTTOM_LEFT, height=60)

    assert second.geometry().bottom() + 1 + host.FLOATING_SPACING == first.y()


def test_right_anchored_widgets_share_their_right_edge(main_window, floating):
    narrow = floating(FloatingAnchor.BOTTOM_RIGHT, width=100)
    wide = floating(FloatingAnchor.BOTTOM_RIGHT, width=160)

    assert narrow.geometry().right() == wide.geometry().right()
    assert wide.x() < narrow.x()


def test_top_right_stack_starts_below_the_stage_controls_overlay(main_window, floating):
    host = main_window.panel_host
    overlay = main_window.stage_controls_overlay
    widget = floating(FloatingAnchor.TOP_RIGHT)

    assert widget.y() == overlay.geometry().bottom() + 1 + host.FLOATING_SPACING
    assert widget.geometry().right() == overlay.geometry().right()


def test_side_panels_move_the_corners(main_window, manager, floating):
    host = main_window.panel_host
    margin = host.FLOATING_MARGIN
    top_left = floating(FloatingAnchor.TOP_LEFT)
    bottom_right = floating(FloatingAnchor.BOTTOM_RIGHT)
    right_edge = bottom_right.geometry().right()

    manager.set_open("tree", True)
    assert top_left.x() == manager.panel("tree").width() + margin

    manager.set_open("tree", False)
    assert top_left.x() == margin

    manager.set_open("inspector", True)
    inspector = manager.panel("inspector")
    assert bottom_right.geometry().right() == inspector.x() - margin - 1
    assert bottom_right.geometry().right() < right_edge


def test_a_very_wide_right_panel_slides_over_right_anchored_widgets(
    main_window, manager, floating
):
    host = main_window.panel_host
    widget = floating(FloatingAnchor.BOTTOM_RIGHT)
    manager.set_open("inspector", True)
    inspector = manager.panel("inspector")

    host.set_panel_size(inspector, host.canvas.width())

    assert widget.x() == host.FLOATING_MARGIN
    assert widget.geometry().intersects(inspector.geometry())


def test_bottom_corners_rest_on_the_console(main_window, manager, floating):
    host = main_window.panel_host
    widget = floating(FloatingAnchor.BOTTOM_LEFT)
    closed_bottom = widget.geometry().bottom()

    manager.set_open("console", True)
    console = manager.panel("console")
    assert widget.geometry().bottom() + 1 + host.FLOATING_MARGIN == console.y()

    manager.set_open("console", False)
    assert widget.geometry().bottom() == closed_bottom


def test_hiding_a_widget_collapses_the_stack(main_window, floating, qtbot):
    host = main_window.panel_host
    first = floating(FloatingAnchor.TOP_LEFT)
    second = floating(FloatingAnchor.TOP_LEFT)
    stacked_y = second.y()
    first_y = first.y()

    first.hide()
    qtbot.waitUntil(lambda: second.y() == first_y, timeout=1000)

    first.show()
    qtbot.waitUntil(lambda: second.y() == stacked_y, timeout=1000)
    assert first.y() == first_y
    assert second.y() == first.geometry().bottom() + 1 + host.FLOATING_SPACING


def test_a_removed_widget_leaves_the_stack(main_window, floating):
    host = main_window.panel_host
    first = floating(FloatingAnchor.TOP_LEFT)
    second = floating(FloatingAnchor.TOP_LEFT)
    first_y = first.y()

    host.remove_floating_widget(first)

    assert second.y() == first_y
