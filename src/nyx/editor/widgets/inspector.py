import typing
import logging

from PySide6 import QtCore, QtWidgets

from .inspector_error_banner import InspectorErrorBanner
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
        self._error_banner = InspectorErrorBanner()
        self._node_components_view = NodeComponentsView()
        self._watched_model: QtCore.QAbstractItemModel | None = None

    def create_layouts(self):
        """Lay out the header above the components."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self._node_header, stretch=0)
        self.main_layout.addWidget(self._error_banner, stretch=0)
        self.main_layout.addWidget(self._node_components_view, stretch=1)

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        return self.main_window.current_stage_graph

    def clear(self):
        """Show no node."""
        self._node_header.set_node(None)
        self._error_banner.set_node(None)
        self._watch_model(None)
        self._node_components_view.setModel(None)

    def _watch_model(self, model: QtCore.QAbstractItemModel | None) -> None:
        """Follow the changes of the model the shown node is in, to update the error.

        Args:
            model (QAbstractItemModel | None): the stage, None to stop following.
        """
        if model is self._watched_model:
            return
        if self._watched_model is not None:
            try:
                self._watched_model.dataChanged.disconnect(self._on_data_changed)
            except (RuntimeError, TypeError):
                pass  # the model is already gone
        self._watched_model = model
        if model is not None:
            model.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self, top_left, bottom_right, roles=None) -> None:
        """Refresh the error when the shown node changes.

        Args:
            top_left (QModelIndex): first changed index.
            bottom_right (QModelIndex): last changed index.
            roles (list[int] | None): changed roles, empty or None for all.
        """
        node = self._error_banner.node
        if node is None or top_left != node.index():
            return
        self._error_banner.refresh()

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
        self._error_banner.set_node(node)
        self._watch_model(node.model() if node else None)
        self._node_components_view.setModel(node.components_model)
