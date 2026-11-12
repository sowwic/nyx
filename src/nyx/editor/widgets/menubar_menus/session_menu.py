import functools
import typing

from PySide6 import QtGui

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class SessionMenu(BaseMenu):
    """Session menu: save and restore sessions and switch between open editors."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&Session", parent=None
    ):
        """Initialize SessionMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def populate(self):
        """Add the session actions and the list of open editors."""
        action = ACTION_REGISTRY.action
        self.addAction(action(ActionId.SAVE_SESSION))
        self.addAction(action(ActionId.LOAD_SESSION))
        self.addAction(action(ActionId.RESTORE_LAST_SESSION))
        self.editors_section = self.addSection("Stages")
        self._editor_actions: list[QtGui.QAction] = []
        self._editors_group = QtGui.QActionGroup(self)
        self.rebuild_editors()

    def create_connections(self):
        """Rebuild the editors list each time the menu opens."""
        self.aboutToShow.connect(self.rebuild_editors)

    def rebuild_editors(self):
        """List every open editor window, checking the active one."""
        for editor_action in self._editor_actions:
            self.removeAction(editor_action)
            self._editors_group.removeAction(editor_action)
            editor_action.deleteLater()
        self._editor_actions.clear()

        mdi_area = self.main_window.mdi_area
        active = mdi_area.currentSubWindow()
        for sub_window in mdi_area.subWindowList():
            editor_action = self.addAction(sub_window.windowTitle())
            editor_action.setCheckable(True)
            editor_action.setChecked(sub_window is active)
            stage_file = sub_window.widget().stage.file_path
            if stage_file:
                editor_action.setToolTip(str(stage_file))
            editor_action.triggered.connect(
                functools.partial(self._activate_editor, sub_window)
            )
            self._editors_group.addAction(editor_action)
            self._editor_actions.append(editor_action)

        if not self._editor_actions:
            placeholder = self.addAction("(No open editors)")
            placeholder.setEnabled(False)
            self._editor_actions.append(placeholder)

    def _activate_editor(self, sub_window, _checked: bool = False):
        """Activate an editor window.

        Args:
            sub_window (QtWidgets.QMdiSubWindow): window to activate.
            _checked (bool): unused triggered state.
        """
        self.main_window.activate_editor_window(sub_window)
