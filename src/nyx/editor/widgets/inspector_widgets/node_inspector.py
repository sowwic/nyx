from __future__ import annotations

import logging
import typing

from PySide6 import QtCore, QtWidgets

from nyx.static.enums import CoreInspectorWidgets
from ..inspector_error_banner import InspectorErrorBanner
from ..inspector_node_header import InspectorNodeHeader
from ...views.node_components_view import NodeComponentsView
from .base import InspectorWidget

if typing.TYPE_CHECKING:
    from nyx.core.node import Node

LOGGER = logging.getLogger(__name__)


class NodeInspectorWidget(InspectorWidget):
    """Header, error and components of a node."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize NodeInspectorWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._watched_model: QtCore.QAbstractItemModel | None = None
        self._create_widgets()
        self._create_layouts()

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the widget."""
        return CoreInspectorWidgets.NODE

    def _create_widgets(self) -> None:
        """Create the node header, the error and the components view."""
        self.node_header = InspectorNodeHeader()
        self.error_banner = InspectorErrorBanner()
        self.node_components_view = NodeComponentsView()

    def _create_layouts(self) -> None:
        """Lay out the header above the components."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.node_header, stretch=0)
        self.main_layout.addWidget(self.error_banner, stretch=0)
        self.main_layout.addWidget(self.node_components_view, stretch=1)

    def clear(self) -> None:
        """Show no node."""
        self.node_header.set_node(None)
        self.error_banner.set_node(None)
        self._watch_model(None)
        self.node_components_view.setModel(None)

    def refresh(self) -> None:
        """Show the node."""
        node: Node | None = self.stage_object
        if node is None:
            self.clear()
            return
        LOGGER.debug(f"Updating inspector: {node.path}")
        self.node_header.set_node(node_uuid=node.uuid)
        self.error_banner.set_node(node)
        self._watch_model(node.model())
        self.node_components_view.setModel(node.components_model)

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
            except RuntimeError, TypeError:
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
        node = self.error_banner.node
        if node is None or top_left != node.index():
            return
        self.error_banner.refresh()
