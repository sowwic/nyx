import typing

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils.io import export_selected_nodes, import_nodes_from_explorer
from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class FileMenu(BaseMenu):
    def __init__(
        self, main_window: NyxEditorMainWindow, title: str = "&File", parent=None
    ):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        register = ACTION_ROUTER.register_handler
        register(ActionId.EXPORT_NODES, export_selected_nodes)
        register(ActionId.IMPORT_NODES, import_nodes_from_explorer)
        register(
            ActionId.REFERENCE_NODES,
            lambda: import_nodes_from_explorer(as_reference=True),
        )

    def populate(self):
        action = ACTION_REGISTRY.action
        self.addSection("Open")
        self.addAction(action(ActionId.NEW_STAGE))
        self.addAction(action(ActionId.OPEN_STAGE))
        self.addAction(action(ActionId.OPEN_STAGE_TAB))
        self.addSection("Save")
        self.addAction(action(ActionId.SAVE_STAGE))
        self.addAction(action(ActionId.SAVE_STAGE_AS))
        self.addSection("Nodes")
        self.addAction(action(ActionId.IMPORT_NODES))
        self.addAction(action(ActionId.REFERENCE_NODES))
        self.addAction(action(ActionId.EXPORT_NODES))
