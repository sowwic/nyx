import logging
import typing

from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from .components_model import NodeComponentsModel

LOGGER = logging.getLogger(__name__)


class NodeComponentsFilterModel(QtCore.QSortFilterProxyModel):
    @QtCore.Property("QVariant")
    def node(self):
        source_model: NodeComponentsModel | None = self.sourceModel()
        if source_model is None:
            LOGGER.error("Can't get node: source model is not set")
            return None
        return source_model.node
