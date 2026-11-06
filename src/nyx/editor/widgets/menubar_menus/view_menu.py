import typing

from PySide6 import QtCore, QtGui

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class ViewMenu(BaseMenu):
    """View menu with the display toggles of the graph views."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&View", parent=None
    ):
        """Initialize ViewMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def create_actions(self):
        """Create the toggle of the viewport debug overlay."""
        self.debug_overlay_action = QtGui.QAction("Viewport Debug Overlay", self)
        self.debug_overlay_action.setCheckable(True)
        self.debug_overlay_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F3))
        self.debug_overlay_action.setToolTip(
            "Show performance numbers in the corner of the graph views"
        )

        self.show_address_names_action = QtGui.QAction("Show Address Names", self)
        self.show_address_names_action.setCheckable(True)
        self.show_address_names_action.setToolTip(
            "Show the names paths are made of, instead of the display names of nodes "
            "and components"
        )

    def populate(self):
        """Add the toggles."""
        self.addAction(self.debug_overlay_action)
        self.addAction(self.show_address_names_action)

    def create_connections(self):
        """Apply the toggle to the config and the views."""
        self.debug_overlay_action.toggled.connect(
            self.main_window.set_viewport_debug_overlay
        )
        self.show_address_names_action.toggled.connect(
            self.main_window.set_show_address_names
        )

    def set_debug_overlay_checked(self, checked: bool):
        """Show the state of the overlay toggle without triggering it.

        Args:
            checked (bool): the overlay is on.
        """
        blocker = QtCore.QSignalBlocker(self.debug_overlay_action)
        self.debug_overlay_action.setChecked(checked)
        blocker.unblock()

    def set_show_address_names_checked(self, checked: bool):
        """Show the state of the address names toggle without triggering it.

        Args:
            checked (bool): address names are shown.
        """
        blocker = QtCore.QSignalBlocker(self.show_address_names_action)
        self.show_address_names_action.setChecked(checked)
        blocker.unblock()
