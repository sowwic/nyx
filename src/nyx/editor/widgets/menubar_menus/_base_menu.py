import typing

from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class BaseMenu(QtWidgets.QMenu):
    """Base menu of the editor menu bar. Subclasses override the setup hooks."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "Menu", parent=None
    ):
        """Initialize BaseMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(title, parent)
        self._main_window = main_window

        self.setTearOffEnabled(True)
        self.create_actions()
        self.populate()
        self.create_connections()

    @property
    def main_window(self) -> NyxEditorMainWindow:
        """NyxEditorMainWindow: editor main window."""
        return self._main_window

    @property
    def current_stage_graph(self):
        """StageGraphEditor | None: editor of the active window."""
        return self.main_window.current_stage_graph

    def create_actions(self):
        """Create actions and register their handlers. Override in subclasses."""
        pass

    def populate(self):
        """Add actions and submenus. Override in subclasses."""
        pass

    def create_connections(self):
        """Connect signals. Override in subclasses."""
        pass
