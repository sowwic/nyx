import typing
from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.core.attribute import Attribute
    from nyx.editor.widgets.attribute_editor import AttributeEditor

LOGGER = get_main_logger()


class AttrTableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, node_attr: "Attribute", text: str) -> None:
        self.node_attr = node_attr
        super().__init__(text)

    def set_node_attr_value(self):
        raise NotImplementedError


class AttrNameTableItem(AttrTableItem):
    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, node_attr.name)
        self.setData(QtCore.Qt.UserRole, self.node_attr.name)
        self.setToolTip(self.node_attr.name)

    def set_node_attr_value(self):
        old_name = self.node_attr.name
        new_name = self.text()
        if old_name == new_name:
            return

        node = self.node_attr.node
        rename_cmd = commands.RenameNodeAttributeCommand(stage=node.stage,
                                                         node=node,
                                                         attr_name=old_name,
                                                         new_attr_name=new_name)
        node.stage.undo_stack.push(rename_cmd)


class AttrTypeTableItem(AttrTableItem):
    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, node_attr.resolved_value.__class__.__name__)
        self.setData(QtCore.Qt.UserRole, type(self.node_attr.resolved_value))
        self.setToolTip(f"Type: {self.data(QtCore.Qt.UserRole)}")


class AttrRawValueTableItem(AttrTableItem):
    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, str(node_attr.value))
        self.setData(QtCore.Qt.UserRole, node_attr.value)
        self.setToolTip(f"Value : {self.node_attr.value} ({type(self.node_attr.value)})")

    def set_node_attr_value(self):
        old_value = self.node_attr.value
        text_value = self.text()
        try:
            new_value = eval(text_value)
        except Exception:
            new_value = text_value

        if old_value == new_value:
            return

        node = self.node_attr.node
        set_attr_cmd = commands.SetNodeAttributeCommand(stage=node.stage,
                                                        node=node,
                                                        attr_name=self.node_attr.name,
                                                        attr_value=new_value)
        node.stage.undo_stack.push(set_attr_cmd)


class AttrResolvedValueTableItem(AttrTableItem):
    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, str(node_attr.resolved_value))
        self.setData(QtCore.Qt.UserRole, self.node_attr.resolved_value)
        self.setToolTip(
            f"Resolved: {self.node_attr.resolved_value} ({type(self.node_attr.resolved_value)})")


class AttrCachedValueTableItem(AttrTableItem):
    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, str(node_attr.cached_value))
        self.setData(QtCore.Qt.UserRole, node_attr.cached_value)
        self.setToolTip(
            f"Cached: {self.node_attr.cached_value} ({type(self.node_attr.cached_value)})")


class AttributesTable(QtWidgets.QTableWidget):

    COLUMNS = ("Name", "Type", "Raw", "Resolved", "Cached")

    def __init__(self, attrib_editor: "AttributeEditor", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(0, len(self.COLUMNS), parent)
        self.main_window = attrib_editor.main_window
        self.tree_view = self.main_window.stage_tree_view

        self.setHorizontalHeaderLabels(self.COLUMNS)

        self.create_connections()

    def create_connections(self):
        self.itemChanged.connect(self.apply_item_edits)
        self.main_window.undo_group.indexChanged.connect(self.update_node_data)

    def update_node_data(self):
        self.setRowCount(0)
        self.blockSignals(True)
        node = self.tree_view.current_item()
        if not node:
            return

        LOGGER.debug("Updating table")
        row_index = 0
        for _, attr in node.attribs.items():
            self.setRowCount(self.rowCount() + 1)
            name_item = AttrNameTableItem(attr)
            type_item = AttrTypeTableItem(attr)
            raw_value_item = AttrRawValueTableItem(attr)
            resolved_value_item = AttrResolvedValueTableItem(attr)
            cached_value_item = AttrCachedValueTableItem(attr)

            self.setItem(row_index, 0, name_item)
            self.setItem(row_index, 1, type_item)
            self.setItem(row_index, 2, raw_value_item)
            self.setItem(row_index, 3, resolved_value_item)
            self.setItem(row_index, 4, cached_value_item)

            row_index += 1

        self.blockSignals(False)

    def apply_item_edits(self, item: AttrTableItem):
        item.set_node_attr_value()
        self.update_node_data()
