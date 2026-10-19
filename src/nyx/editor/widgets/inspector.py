import typing
import logging

from PySide6 import QtWidgets

from .inspector_node_header import InspectorNodeHeader
from ..views.node_components_view import NodeComponentsView

if typing.TYPE_CHECKING:
    from ..main_window import NyxEditorMainWindow
    from .stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class Inspector(QtWidgets.QWidget):
    """Dock content showing the header and components of the selected node."""

    def __init__(
        self, main_window: NyxEditorMainWindow, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize Inspector.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.main_window: NyxEditorMainWindow = main_window

        self.create_actions()
        self.create_widgets()
        self.create_layouts()

    def create_actions(self):
        """Create actions. The inspector has none."""
        pass

    def create_widgets(self):
        """Create the node header and components view."""
        self._node_header = InspectorNodeHeader()
        self._node_components_view = NodeComponentsView()

    def create_layouts(self):
        """Lay out the header above the components."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self._node_header, stretch=0)
        self.main_layout.addWidget(self._node_components_view, stretch=1)

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        return self.main_window.current_stage_graph

    def clear(self):
        """Show no node."""
        self._node_header.set_node(None)
        self._node_components_view.setModel(None)

    def update_data(self):
        """Show the selected node of the active editor, or the root node."""
        if self.current_stage_graph is None:
            self.clear()
            self.setEnabled(False)
            return

        self.setEnabled(True)
        selected_nodes = self.current_stage_graph.list_selected_nodes()
        node = (
            selected_nodes[0]
            if selected_nodes
            else self.current_stage_graph.stage.root_node
        )
        LOGGER.debug(f"Updating inspector: {node.path}")
        self._node_header.set_node(node_uuid=node.uuid if node else None)
        self._node_components_view.setModel(node.components_model)
