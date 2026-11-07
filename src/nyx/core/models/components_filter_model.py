import logging
import typing

from PySide6 import QtCore

from ..node_component import NodeComponent

if typing.TYPE_CHECKING:
    from .components_model import NodeComponentsModel

LOGGER = logging.getLogger(__name__)


class NodeComponentsFilterModel(QtCore.QSortFilterProxyModel):
    """Filter proxy over a node's components model."""

    @QtCore.Property("QVariant")
    def node(self):
        """Node | None: node of the source model, None if no source model is set."""
        source_model: NodeComponentsModel | None = self.sourceModel()
        if source_model is None:
            LOGGER.error("Can't get node: source model is not set")
            return None
        return source_model.node

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        """Reject components hidden from the inspector, then apply the text filter.

        Args:
            source_row (int): row in the source model.
            source_parent (QtCore.QModelIndex): parent index in the source model.

        Returns:
            bool: the row is shown.
        """
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        if source_index.data(NodeComponent.Roles.IS_INSPECTOR_HIDDEN):
            return False
        return super().filterAcceptsRow(source_row, source_parent)
