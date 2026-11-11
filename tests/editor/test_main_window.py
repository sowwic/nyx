import pytest
from unittest import mock

from PySide6 import QtCore, QtGui, QtWidgets

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
        ActionId.IMPORT_STAGE,
        ActionId.REFERENCE_STAGE,
    ):
        assert ACTION_REGISTRY.action(action_id) in file_actions

    edit_actions = main_window.menubar_edit_menu.actions()
    assert ACTION_REGISTRY.action(ActionId.RENAME_NODE) in edit_actions
    assert ACTION_REGISTRY.action(ActionId.RESET_CONFIG) in edit_actions
    assert edit_actions.index(ACTION_REGISTRY.action(ActionId.EDIT_CONFIG)) + 1 == (
        edit_actions.index(ACTION_REGISTRY.action(ActionId.RESET_CONFIG))
    )
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


@pytest.fixture
def recent_files(main_window, monkeypatch):
    session = main_window.config.values.editor_session
    monkeypatch.setattr(session, "recent_files", [])
    monkeypatch.setattr(main_window.config, "save", mock.Mock())
    return session.recent_files


def _make_stage_file(path, create_node):
    from nyx.api.v1 import Stage

    stage = Stage()
    create_node(stage, "n")
    stage.export_json(path)
    return str(path)


def test_save_as_adds_recent_file_once(
    main_window, stage_editor, recent_files, tmp_path, monkeypatch
):
    target = tmp_path / "saved.nyx"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )
    stage_editor.on_stage_save_as()
    stage_editor.on_stage_save()
    assert recent_files == [str(target)]


def test_recent_files_capped(main_window, recent_files, tmp_path):
    max_recent_files = main_window.config.values.editor_session.max_recent_files
    for i in range(max_recent_files + 3):
        main_window.add_recent_file(str(tmp_path / f"{i}.nyx"))
    assert len(recent_files) == max_recent_files
    assert recent_files[0] == str(tmp_path / f"{max_recent_files + 2}.nyx")


def test_recent_menu_placeholder_when_empty(main_window, recent_files):
    menu = main_window.menubar_file_menu
    menu.rebuild_recent_menu()
    actions = menu.recent_menu.actions()
    assert [a.text() for a in actions] == ["(No recent files)"]
    assert not actions[0].isEnabled()


def test_recent_action_opens_in_new_editor(
    main_window, stage_editor, recent_files, tmp_path, create_node
):
    target = _make_stage_file(tmp_path / "recent.nyx", create_node)
    main_window.add_recent_file(target)
    menu = main_window.menubar_file_menu
    menu.rebuild_recent_menu()
    menu.recent_menu.actions()[0].trigger()

    assert len(main_window.mdi_area.subWindowList()) == 2
    assert main_window.current_stage_graph is not stage_editor
    assert main_window.current_stage_graph.stage.file_path.name == "recent.nyx"


def test_recent_action_creates_window_when_none(
    main_window, recent_files, tmp_path, create_node
):
    target = _make_stage_file(tmp_path / "recent.nyx", create_node)
    main_window.on_stage_open_recent(target)
    assert len(main_window.mdi_area.subWindowList()) == 1
    assert main_window.current_stage_graph.stage.file_path.name == "recent.nyx"


def test_missing_recent_file_is_removed(main_window, recent_files, tmp_path):
    missing = str(tmp_path / "gone.nyx")
    main_window.add_recent_file(missing)
    main_window.on_stage_open_recent(missing)
    assert recent_files == []
    assert main_window.mdi_area.subWindowList() == []


def test_open_recent_activates_existing_window(
    main_window, recent_files, tmp_path, create_node
):
    target = _make_stage_file(tmp_path / "recent.nyx", create_node)
    main_window.on_stage_open_recent(target)
    first = main_window.current_mdi_window
    main_window.on_stage_new()
    assert main_window.current_mdi_window is not first

    main_window.on_stage_open_recent(target)

    assert len(main_window.mdi_area.subWindowList()) == 2
    assert main_window.current_mdi_window is first


def test_open_dialog_activates_existing_window(
    main_window, recent_files, tmp_path, create_node, monkeypatch
):
    target = _make_stage_file(tmp_path / "recent.nyx", create_node)
    main_window.on_stage_open_recent(target)
    first = main_window.current_mdi_window
    main_window.on_stage_new()
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: (str(target), "")
    )

    main_window.on_stage_open(tabbed=True)

    assert len(main_window.mdi_area.subWindowList()) == 2
    assert main_window.current_mdi_window is first


def test_session_save_and_load(
    main_window, recent_files, tmp_path, create_node, monkeypatch
):
    first = _make_stage_file(tmp_path / "one.nyx", create_node)
    second = _make_stage_file(tmp_path / "two.nyx", create_node)
    main_window.on_stage_open_recent(first)
    main_window.on_stage_open_recent(second)
    session_file = tmp_path / "work.nyxsession"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(session_file), "")
    )
    main_window.on_session_save()
    for sub_wnd in main_window.mdi_area.subWindowList():
        sub_wnd.close()
    assert main_window.mdi_area.subWindowList() == []

    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: (str(session_file), "")
    )
    main_window.on_session_load()

    opened = {
        w.widget().stage.file_path.name for w in main_window.mdi_area.subWindowList()
    }
    assert opened == {"one.nyx", "two.nyx"}


def test_session_restores_active_stage_and_view(
    main_window, recent_files, tmp_path, create_node, monkeypatch, qtbot
):
    first = _make_stage_file(tmp_path / "one.nyx", create_node)
    second = _make_stage_file(tmp_path / "two.nyx", create_node)
    main_window.on_stage_open_recent(first)
    main_window.current_stage_graph.gr_view.apply_view_state(
        {"zoom": 7.0, "center": [120.0, -40.0]}
    )
    main_window.on_stage_open_recent(second)
    main_window.activate_window_for_file(first)

    session_file = tmp_path / "work.nyxsession"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(session_file), "")
    )
    main_window.on_session_save()
    for sub_wnd in main_window.mdi_area.subWindowList():
        sub_wnd.close()

    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *a, **k: (str(session_file), "")
    )
    main_window.on_session_load()
    qtbot.wait(20)

    restored = main_window.current_stage_graph
    assert restored.stage.file_path.name == "one.nyx"
    assert restored.gr_view.zoom == pytest.approx(7.0)
    center = restored.gr_view.get_view_state()["center"]
    assert center == pytest.approx([120.0, -40.0], abs=5.0)


def test_close_saves_last_session_and_restore_reopens(
    main_window, recent_files, tmp_path, create_node, monkeypatch
):
    from nyx.editor import main_window as main_window_module

    last_session = tmp_path / "last.nyxsession"
    monkeypatch.setattr(main_window_module, "LAST_SESSION_FILE_PATH", last_session)
    target = _make_stage_file(tmp_path / "one.nyx", create_node)
    main_window.on_stage_open_recent(target)
    monkeypatch.setattr(main_window, "save_config_value", lambda: None)

    main_window.closeEvent(QtGui.QCloseEvent())
    assert last_session.is_file()

    for sub_wnd in main_window.mdi_area.subWindowList():
        sub_wnd.close()
    main_window.on_session_restore_last()
    assert main_window.current_stage_graph.stage.file_path.name == "one.nyx"


def test_session_load_with_open_stages_creates_no_duplicates(
    main_window, recent_files, tmp_path, create_node, monkeypatch
):
    first = _make_stage_file(tmp_path / "one.nyx", create_node)
    second = _make_stage_file(tmp_path / "two.nyx", create_node)
    main_window.on_stage_open_recent(first)
    main_window.on_stage_open_recent(second)
    session_file = tmp_path / "work.nyxsession"
    main_window.save_session(session_file)

    main_window.load_session(session_file)
    main_window.load_session(session_file)

    paths = [
        w.widget().stage.file_path.name for w in main_window.mdi_area.subWindowList()
    ]
    assert sorted(paths) == ["one.nyx", "two.nyx"]


def test_session_menu_lists_open_editors_and_activates(
    main_window, recent_files, tmp_path, create_node
):
    menu = main_window.menubar_session_menu
    menu.rebuild_editors()
    assert [a.text() for a in menu._editor_actions] == ["(No open editors)"]

    first = _make_stage_file(tmp_path / "one.nyx", create_node)
    second = _make_stage_file(tmp_path / "two.nyx", create_node)
    main_window.on_stage_open_recent(first)
    first_wnd = main_window.current_mdi_window
    main_window.on_stage_open_recent(second)
    menu.rebuild_editors()

    actions = menu._editor_actions
    assert len(actions) == 2
    assert [a.isChecked() for a in actions] == [False, True]

    actions[0].trigger()
    assert main_window.current_mdi_window is first_wnd


def test_config_action_opens_the_config_editor_once(main_window, monkeypatch):
    from json_config_qt.editor_dialog import ConfigEditorDialog

    ACTION_REGISTRY.action(ActionId.EDIT_CONFIG).trigger()
    dialog = ConfigEditorDialog.show_for(main_window.config)
    try:
        assert dialog.isVisible()
        ACTION_REGISTRY.action(ActionId.EDIT_CONFIG).trigger()
        assert ConfigEditorDialog.show_for(main_window.config) is dialog
    finally:
        dialog.close()


def test_saving_in_the_config_editor_applies_the_config(main_window, monkeypatch, qtbot):
    apply = mock.Mock()
    monkeypatch.setattr(main_window, "apply_config_values", apply)
    dialog = main_window.show_config_editor()
    try:
        dialog.saved.emit("user")
        qtbot.waitUntil(lambda: apply.called, timeout=2000)
        apply.reset_mock()
        main_window.show_config_editor()  # reused dialog must not connect twice
        dialog.saved.emit("user")
        qtbot.wait(100)
        apply.assert_called_once_with()
    finally:
        dialog.close()


def test_always_on_top_toggle_applies_flag_and_config(main_window):
    hint = QtCore.Qt.WindowType.WindowStaysOnTopHint
    action = main_window.menubar_view_menu.always_on_top_action
    try:
        action.trigger()
        assert main_window.config.values.main_window.is_always_on_top
        assert main_window.windowFlags() & hint

        action.trigger()
        assert not main_window.config.values.main_window.is_always_on_top
        assert not main_window.windowFlags() & hint
    finally:
        main_window.set_always_on_top(False)


def test_always_on_top_config_value_is_applied(main_window):
    hint = QtCore.Qt.WindowType.WindowStaysOnTopHint
    action = main_window.menubar_view_menu.always_on_top_action
    try:
        main_window.config.values.main_window.is_always_on_top = True
        main_window.apply_config_values()
        assert main_window.windowFlags() & hint
        assert action.isChecked()
    finally:
        main_window.set_always_on_top(False)
