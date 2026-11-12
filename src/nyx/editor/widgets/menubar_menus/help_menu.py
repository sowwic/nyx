import typing

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class HelpMenu(BaseMenu):
    """Help menu with the documentation link and the about dialog."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&Help", parent=None
    ):
        """Initialize HelpMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def create_actions(self):
        """Get the shared actions, their handlers are set by the main window."""
        action = ACTION_REGISTRY.action
        self.documentation_action = action(ActionId.DOCUMENTATION)
        self.about_action = action(ActionId.ABOUT)

    def populate(self):
        """Add the actions."""
        self.addAction(self.documentation_action)
        self.addAction(self.about_action)
