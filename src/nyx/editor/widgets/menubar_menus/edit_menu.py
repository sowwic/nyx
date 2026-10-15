import typing

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class EditMenu(BaseMenu):
    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&Edit", parent=None
    ):
        super().__init__(main_window, title, parent)

    def create_actions(self):
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
        action = ACTION_REGISTRY.action
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        self.addSeparator()
        self.addAction(action(ActionId.RENAME_NODE))
        self.addSection("Editor")
        self.addAction(action(ActionId.RESET_CONFIG))

    def on_rename_selected_node(self):
        if not self.main_window.current_stage_graph:
            return
        self.main_window.current_stage_graph.gr_stage.start_selected_node_rename()
