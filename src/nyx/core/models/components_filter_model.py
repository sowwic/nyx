import logging
import typing

from PySide6 import QtCore

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
