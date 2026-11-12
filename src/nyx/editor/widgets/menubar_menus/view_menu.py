import typing

from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class ViewMenu(BaseMenu):
    """View menu with the display toggles of the editor."""

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
        """Get the shared toggle actions, their handlers are set by the main window."""
        action = ACTION_REGISTRY.action
        self.debug_overlay_action = action(ActionId.VIEWPORT_DEBUG_OVERLAY)
        self.show_address_names_action = action(ActionId.SHOW_ADDRESS_NAMES)
        self.always_on_top_action = action(ActionId.ALWAYS_ON_TOP)

    def populate(self):
        """Add the toggles."""
        self.addAction(self.debug_overlay_action)
        self.addAction(self.show_address_names_action)
        self.addSeparator()
        self.addAction(self.always_on_top_action)

    def set_debug_overlay_checked(self, checked: bool):
        """Show the state of the overlay toggle without triggering it.

        Args:
            checked (bool): the overlay is on.
        """
        self._set_checked(self.debug_overlay_action, checked)

    def set_show_address_names_checked(self, checked: bool):
        """Show the state of the address names toggle without triggering it.

        Args:
            checked (bool): address names are shown.
        """
        self._set_checked(self.show_address_names_action, checked)

    def set_always_on_top_checked(self, checked: bool):
        """Show the state of the always on top toggle without triggering it.

        Args:
            checked (bool): the window stays on top.
        """
        self._set_checked(self.always_on_top_action, checked)

    @staticmethod
    def _set_checked(action, checked: bool):
        """Set the checked state of a toggle without emitting its signals.

        Args:
            action (QtGui.QAction): toggle action.
            checked (bool): checked state.
        """
        blocker = QtCore.QSignalBlocker(action)
        action.setChecked(checked)
        blocker.unblock()
