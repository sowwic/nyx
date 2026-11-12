from unittest import mock

from PySide6 import QtGui

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.dialogs.about_dialog import AboutDialog
from nyx.static.vars import DOCUMENTATION_URL


def test_help_menu_in_menubar(main_window):
    titles = [action.text() for action in main_window.menuBar().actions()]
    assert titles[-1] == "&Help"
    texts = [action.text() for action in main_window.menubar_help_menu.actions()]
    assert texts == ["Documentation", "About"]
    assert not main_window.menubar_help_menu.documentation_action.icon().isNull()


def test_documentation_opens_url(main_window):
    with mock.patch.object(QtGui.QDesktopServices, "openUrl") as open_url:
        ACTION_REGISTRY.action(ActionId.DOCUMENTATION).trigger()
    assert open_url.call_args.args[0].toString() == DOCUMENTATION_URL


def test_about_dialog(qtbot, main_window):
    dialog = AboutDialog(main_window)
    qtbot.addWidget(dialog)
    assert not dialog.icon_label.pixmap().isNull()
    assert "Version" in dialog.info_label.text()
    with mock.patch.object(AboutDialog, "exec") as exec_:
        ACTION_REGISTRY.action(ActionId.ABOUT).trigger()
    exec_.assert_called_once()
