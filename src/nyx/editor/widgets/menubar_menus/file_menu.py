import functools
import pathlib
import typing

from PySide6 import QtGui


from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils.io import import_stages_from_explorer
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class FileMenu(BaseMenu):
    """File menu: stage open and save, recent files and stage import and reference."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&File", parent=None
    ):
        """Initialize FileMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def create_actions(self):
        """Register the handlers of the stage import and reference actions."""
        register = ACTION_ROUTER.register_handler
        register(ActionId.IMPORT_STAGE, import_stages_from_explorer)
        register(
            ActionId.REFERENCE_STAGE,
            lambda: import_stages_from_explorer(as_reference=True),
        )

    def populate(self):
        """Add the file actions and the recent files submenu."""
        action = ACTION_REGISTRY.action
        self.addSection("Open")
        self.addAction(action(ActionId.NEW_STAGE))
        self.addAction(action(ActionId.OPEN_STAGE))
        self.addAction(action(ActionId.OPEN_STAGE_TAB))
        self.addAction(action(ActionId.IMPORT_STAGE))
        self.addAction(action(ActionId.REFERENCE_STAGE))
        self.recent_menu = self.addMenu("Recent Files...")
        self.recent_menu.setIcon(QtGui.QIcon(":/icons/history"))
        self.recent_menu.setToolTipsVisible(True)
        self.recent_menu.aboutToShow.connect(self.rebuild_recent_menu)
        self.rebuild_recent_menu()
        self.addSection("Save")
        self.addAction(action(ActionId.SAVE_STAGE))
        self.addAction(action(ActionId.SAVE_STAGE_AS))

    def rebuild_recent_menu(self):
        """Refill the recent files submenu from the session."""
        self.recent_menu.clear()
        recent_files = self.main_window.config.values.editor_session.recent_files
        if not recent_files:
            placeholder = self.recent_menu.addAction("(No recent files)")
            placeholder.setEnabled(False)
            return

        for file_path in list(recent_files):
            recent_action = self.recent_menu.addAction(pathlib.Path(file_path).name)
            recent_action.setToolTip(file_path)
            recent_action.setStatusTip(file_path)
            recent_action.triggered.connect(
                functools.partial(self._open_recent, file_path)
            )

    def _open_recent(self, file_path: str, _checked: bool = False):
        """Open a recent file.

        Args:
            file_path (str): stage file path.
            _checked (bool): unused triggered state.
        """
        self.main_window.on_stage_open_recent(file_path)
