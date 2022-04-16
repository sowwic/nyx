from PySide2 import QtGui
from nyx import get_main_logger

LOGGER = get_main_logger()


class Stage(QtGui.QStandardItemModel):
    def __init__(self) -> None:
        super().__init__()

    def add_node(self, node: QtGui.QStandardItem, parent: QtGui.QStandardItem = None):
        if parent is None:
            parent = self.invisibleRootItem()
        parent.appendRow(node)
        LOGGER.debug(f"Added node {node}")
