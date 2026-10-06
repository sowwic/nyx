import typing
import logging

# from PySide6 import QtGui
from PySide6 import QtWidgets


from ..views.node_components_view import NodeComponentsView
# from nyx.core.models.registry_model import RegistryListModel
# from nyx.core.plugin_subsystem.registry import NYX_REGISTRY

if typing.TYPE_CHECKING:
    from ..main_window import NyxEditorMainWindow
    from .stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class Inspector(QtWidgets.QWidget):
    def __init__(
        self, main_window: NyxEditorMainWindow, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.main_window: NyxEditorMainWindow = main_window

        self.create_actions()
        self.create_widgets()
        self.create_layouts()

    def create_actions(self):
        pass

    def create_widgets(self):
        self._node_components_view = NodeComponentsView()

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self._node_components_view)

    @property
    def current_stage_graph(self) -> StageGraphEditor:
        return self.main_window.current_stage_graph

    def update_data(self):
        selected_nodes = self.current_stage_graph.list_selected_nodes()
        node = (
            selected_nodes[0]
            if selected_nodes
            else self.current_stage_graph.stage.root_node
        )
        LOGGER.debug(f"Updating inspector: {node.path}")
        self._node_components_view.setModel(node.components_model)
