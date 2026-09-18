import typing
import logging

# from PySide6 import QtGui
from PySide6 import QtWidgets


from ..views.node_components_view import NodeComponentsView
from nyx.core.models.registry_model import RegistryListModel
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY

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
        self.main_layout.addWidget(self._node_components_view)
        self._node_components_view.setModel(
            RegistryListModel(lambda: NYX_REGISTRY.get_plugins_types_dict())
        )

    @property
    def current_stage_graph(self) -> StageGraphEditor:
        return self.main_window.current_stage_graph

    def update_data(self):
        selected_nodes = self.current_stage_graph.list_selected_nodes()
        if not selected_nodes:
            LOGGER.info("TODO: Inspector::set_place_holder_widget")
            return

        LOGGER.debug(selected_nodes)
        for node in selected_nodes:
            LOGGER.info("TODO: Inspector::update_data %s", node)
