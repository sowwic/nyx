from PySide2 import QtGui
from nyx.core.serializable import Serializable
from nyx import get_main_logger

LOGGER = get_main_logger()


class Stage(QtGui.QStandardItemModel, Serializable):
    def __init__(self) -> None:
        super().__init__()

    def list_root_children(self):
        return [self.invisibleRootItem().child(row) for row in range(self.invisibleRootItem().rowCount())]

    def add_node(self, node: QtGui.QStandardItem, parent: QtGui.QStandardItem = None):
        if parent is None:
            parent = self.invisibleRootItem()
        parent.appendRow(node)
        LOGGER.debug(f"Added node {node}")

    def delete_node(self, node):
        self.beginResetModel()
        parent = node.parent() or self.invisibleRootItem()
        self.removeRow(node.row(), parent.index())
        self.endResetModel()
