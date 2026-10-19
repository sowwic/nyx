import typing
# from PySide6 import QtGui

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class WindowMenu(BaseMenu):
    """Window menu with the visibility toggles of the dock widgets."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&Window", parent=None
    ):
        """Initialize WindowMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def populate(self):
        """Add a toggle action per dock widget."""
        self.addSection("Visibility")
        for dock_widget in self.main_window.dock_widgets:
            self.addAction(dock_widget.toggleViewAction())
