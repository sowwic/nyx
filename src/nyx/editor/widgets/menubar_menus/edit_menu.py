import typing

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class EditMenu(BaseMenu):
    """Edit menu: undo, redo, rename and editor reset."""

    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&Edit", parent=None
    ):
        """Initialize EditMenu.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            title (str): menu title.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(main_window, title, parent)

    def create_actions(self):
        """Create the undo and redo actions and register the rename handler."""
        undo_group = self.main_window.undo_group
        self.undo_action = ACTION_REGISTRY.adopt_action(
            ActionId.UNDO, undo_group.createUndoAction(self)
        )
        self.redo_action = ACTION_REGISTRY.adopt_action(
            ActionId.REDO, undo_group.createRedoAction(self)
        )
        ACTION_ROUTER.register_handler(
            ActionId.RENAME_NODE, self.on_rename_selected_node
        )

    def populate(self):
        """Add the edit actions."""
        action = ACTION_REGISTRY.action
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        self.addSeparator()
        self.addAction(action(ActionId.RENAME_NODE))
        self.addSection("Editor")
        self.addAction(action(ActionId.RESET_CONFIG))

    def on_rename_selected_node(self):
        """Start renaming the selected node in the active graph."""
        if not self.main_window.current_stage_graph:
            return
        self.main_window.current_stage_graph.gr_stage.start_selected_node_rename()
