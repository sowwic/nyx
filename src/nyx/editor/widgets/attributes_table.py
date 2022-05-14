import typing
from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
# from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.core import Node

LOGGER = get_main_logger()


class AttributesTable(QtWidgets.QTableWidget):

    COLUMNS = ("Name", "Type", "Raw", "Resolved", "Cached")

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(self.COLUMNS)

    def update_node_data(self, node: "Node"):
        self.blockSignals(True)
        self.setRowCount(0)
        if not node:
            return

        LOGGER.debug("Updating table")
        row_index = 0
        for attr_name, attr in node.attribs.items():
            self.setRowCount(self.rowCount() + 1)
            name_item = QtWidgets.QTableWidgetItem(attr_name)
            raw_value_item = QtWidgets.QTableWidgetItem(str(attr.value))
            raw_value_item.setData(QtCore.Qt.UserRole, attr.value)
            resolved_value_item = QtWidgets.QTableWidgetItem(str(attr.resolved_value))
            resolved_value_item.setData(QtCore.Qt.UserRole, attr.resolved_value)
            cached_value_item = QtWidgets.QTableWidgetItem(str(attr.cached_value))
            cached_value_item.setData(QtCore.Qt.UserRole, attr.cached_value)
            self.setItem(row_index, 0, name_item)
            self.setItem(row_index, 2, raw_value_item)
            self.setItem(row_index, 3, resolved_value_item)
            self.setItem(row_index, 4, cached_value_item)

            row_index += 1

        self.blockSignals(False)
