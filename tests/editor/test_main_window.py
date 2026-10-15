from unittest import mock

from PySide6 import QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.static.enums import EditorUIObject


def test_no_stage_by_default(main_window):
    assert main_window.current_stage_graph is None
    assert main_window.windowTitle() == main_window.DEFAULT_TITLE
    assert main_window.stage_tree_view.stage is None


def test_new_stage_opens_sub_window(main_window, stage_editor):
    assert len(main_window.mdi_area.subWindowList()) == 1
    assert main_window.current_stage_graph is stage_editor
    assert stage_editor.windowTitle() in main_window.windowTitle()


def test_new_stage_action_creates_tabs(main_window, stage_editor):
    ACTION_REGISTRY.action(ActionId.NEW_STAGE).trigger()
    assert len(main_window.mdi_area.subWindowList()) == 2


def test_switching_sub_window_switches_stage_and_undo_stack(main_window, stage_editor):
    first = stage_editor
    main_window.on_stage_new()
    second = main_window.current_stage_graph
    assert second is not first
    assert main_window.stage_tree_view.stage is second.stage

    main_window.mdi_area.setActiveSubWindow(first.parentWidget())
    assert main_window.current_stage_graph is first
    assert main_window.stage_tree_view.stage is first.stage
    assert main_window.undo_group.activeStack() is first.stage.undo_stack


def test_closing_last_stage_clears_tree_view(main_window, stage_editor):
    stage_editor.maybe_save = lambda: True
    stage_editor.parentWidget().close()
    QtWidgets.QApplication.processEvents()
    assert main_window.current_stage_graph is None
    assert main_window.stage_tree_view.stage is None
    assert main_window.undo_group.activeStack() is None


def test_title_tracks_active_stage(main_window, stage_editor, tmp_path):
    target = tmp_path / "titled.nyx"
    stage_editor.stage.export_json(target)
    stage_editor.update_title()
    main_window.update_title()
    assert main_window.windowTitle().endswith("titled.nyx")


def test_execute_without_stage_is_noop(main_window):
    main_window.execute_stage_graph()
    main_window.execute_from_selected_node()


def test_execute_stage_starts_crawler(main_window, stage_editor):
    with mock.patch.object(type(stage_editor.stage.crawler), "start") as start:
        main_window.execute_stage_graph()
    start.assert_called_once_with()


def test_execute_from_selected_requires_selection(main_window, stage_editor, caplog):
    with (
        caplog.at_level("WARNING"),
        mock.patch.object(type(stage_editor.stage.crawler), "start") as start,
    ):
        main_window.execute_from_selected_node()
    start.assert_not_called()
    assert "No node selected" in caplog.text


def test_execute_from_selected_uses_last_selected(
    main_window, stage_editor, create_node
):
    from PySide6 import QtCore

    node = create_node(stage_editor.stage, "start")
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    with mock.patch.object(type(stage_editor.stage.crawler), "start") as start:
        main_window.execute_from_selected_node()
    start.assert_called_once_with(start_node=node)


def test_save_actions_delegate_to_current_editor(main_window, stage_editor):
    stage_editor.on_stage_save = mock.Mock()
    stage_editor.on_stage_save_as = mock.Mock()
    ACTION_REGISTRY.action(ActionId.SAVE_STAGE).trigger()
    ACTION_REGISTRY.action(ActionId.SAVE_STAGE_AS).trigger()
    stage_editor.on_stage_save.assert_called_once_with()
    stage_editor.on_stage_save_as.assert_called_once_with()


def test_save_without_stage_is_noop(main_window):
    main_window.on_stage_save()
    main_window.on_stage_save_as()


def test_open_cancelled_removes_new_window(main_window, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: ("", "")
    )
    main_window.on_stage_open()
    assert main_window.mdi_area.subWindowList() == []


def test_open_loads_file_into_new_window(
    main_window, tmp_path, create_node, monkeypatch
):
    from nyx.api.v1 import Stage

    stage = Stage()
    create_node(stage, "from_disk")
    target = tmp_path / "disk.nyx"
    stage.export_json(target)
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: (str(target), "")
    )

    main_window.on_stage_open()

    editor = main_window.current_stage_graph
    assert editor.stage.file_path.name == "disk.nyx"
    assert [n.name for n in editor.stage.list_children(editor.stage.root_node)] == [
        "from_disk"
    ]


def test_close_event_ignored_when_save_cancelled(main_window, stage_editor):
    from PySide6 import QtGui

    stage_editor.maybe_save = lambda: False
    event = QtGui.QCloseEvent()
    main_window.closeEvent(event)
    assert not event.isAccepted()


def test_all_docks_present(main_window):
    names = {dock.objectName() for dock in main_window.dock_widgets}
    assert EditorUIObject.NODES_PALETTE_DOCK in names
    assert all(dock.parent() is main_window for dock in main_window.dock_widgets)


def test_window_menu_lists_every_dock(main_window):
    window_menu = main_window.menubar_window_menu
    toggles = [a for a in window_menu.actions() if not a.isSeparator()]
    for dock in main_window.dock_widgets:
        assert dock.toggleViewAction() in toggles


def test_menus_use_registry_actions(main_window):
    file_actions = main_window.menubar_file_menu.actions()
    for action_id in (
        ActionId.NEW_STAGE,
        ActionId.OPEN_STAGE,
        ActionId.SAVE_STAGE,
        ActionId.IMPORT_NODES,
        ActionId.EXPORT_NODES,
    ):
        assert ACTION_REGISTRY.action(action_id) in file_actions

    edit_actions = main_window.menubar_edit_menu.actions()
    assert ACTION_REGISTRY.action(ActionId.RENAME_NODE) in edit_actions
    assert ACTION_REGISTRY.action(ActionId.RESET_CONFIG) in edit_actions
    assert main_window.menubar_edit_menu.undo_action in edit_actions


def test_undo_redo_follow_active_stack(main_window, stage_editor, create_node):
    edit_menu = main_window.menubar_edit_menu
    assert not edit_menu.undo_action.isEnabled()
    create_node(stage_editor.stage, "n")
    assert edit_menu.undo_action.isEnabled()
    edit_menu.undo_action.trigger()
    assert edit_menu.redo_action.isEnabled()


def test_toolbar_exposes_registry_actions(main_window):
    toolbar_actions = main_window.findChild(QtWidgets.QToolBar).actions()
    for action_id in (ActionId.CREATE_NODE, ActionId.EXECUTE_STAGE):
        assert ACTION_REGISTRY.action(action_id) in toolbar_actions


def test_create_node_action_opens_palette(main_window, stage_editor, monkeypatch):
    from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

    popup = mock.Mock()
    monkeypatch.setattr(PopupNodesPalette, "popup_centered", popup)
    ACTION_REGISTRY.action(ActionId.CREATE_NODE).trigger()
    popup.assert_called_once()


def test_reset_config_action_resets_application_config(main_window, monkeypatch):
    reset = mock.Mock()
    monkeypatch.setattr(main_window.config, "reset", reset)
    monkeypatch.setattr(main_window, "apply_config_values", mock.Mock())
    ACTION_REGISTRY.action(ActionId.RESET_CONFIG).trigger()
    reset.assert_called_once_with()
