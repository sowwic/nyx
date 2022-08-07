import typing
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import commands

if typing.TYPE_CHECKING:
    # from nyx.core import Node
    from nyx.core.attribute import Attribute
    from nyx.editor.widgets.attribute_editor import AttributeEditor

LOGGER = get_main_logger()


class AttrTableItem(QtWidgets.QTableWidgetItem):
    EDITABLE = True

    def __init__(self, node_attr: "Attribute", text: str) -> None:
        super().__init__(text)
        self.node_attr = node_attr
        if not self.EDITABLE:
            self.setFlags(self.flags() ^ QtCore.Qt.ItemIsEditable)

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
    EDITABLE = False

    def __init__(self, node_attr: "Attribute") -> None:
        value = node_attr.resolved_value
        if node_attr.cached_value is not None and node_attr.cached_value != value:
            value = node_attr.cached_value

        super().__init__(node_attr, value.__class__.__name__)
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
    EDITABLE = False

    def __init__(self, node_attr: "Attribute") -> None:
        super().__init__(node_attr, str(node_attr.resolved_value))
        self.setData(QtCore.Qt.UserRole, self.node_attr.resolved_value)
        self.setToolTip(
            f"Resolved: {self.node_attr.resolved_value} ({type(self.node_attr.resolved_value)})")


class AttrCachedValueTableItem(AttrTableItem):
    EDITABLE = False

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
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.create_actions()
        self.create_connections()

    def create_actions(self):
        self.add_attr_action = QtWidgets.QAction("Add new attribute", self)
        self.delete_selected_attr_action = QtWidgets.QAction("Delete selected", self)
        self.update_action = QtWidgets.QAction("Update", self)
        self.copy_selected_attr_path_action = QtWidgets.QAction("Copy as path", self)
        self.clear_cache_for_selected_action = QtWidgets.QAction("Clear cached value", self)

        self.add_attr_action.triggered.connect(self.add_new_attribute)
        self.update_action.triggered.connect(self.update_node_data)
        self.delete_selected_attr_action.triggered.connect(self.delete_selected_attr)
        self.copy_selected_attr_path_action.triggered.connect(self.copy_selected_attr_path)
        self.clear_cache_for_selected_action.triggered.connect(self.clear_cache_for_selected_attrs)

    def create_connections(self):
        self.itemChanged.connect(self.apply_item_edits)
        self.tree_view.selection_changed.connect(self.update_node_data)
        self.main_window.undo_group.indexChanged.connect(self.update_node_data)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_node_data(self):
        self.setRowCount(0)
        self.blockSignals(True)
        node = self.tree_view.current_node()
        if not node:
            return

        self.set_data_from_node(node)
        self.blockSignals(False)

    def set_data_from_node(self, node):
        # LOGGER.debug("Updating attr table")
        row_index = 0
        for _, attr in node.attribs.items():
            attr.resolve()
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

    def apply_item_edits(self, item: AttrTableItem):
        item.set_node_attr_value()
        self.update_node_data()

    def add_new_attribute(self):
        node = self.tree_view.current_node()
        if not node:
            return
        add_attr_cmd = commands.AddNodeAttributeCommand(stage=node.stage,
                                                        node=node,
                                                        attr_name="attr",
                                                        attr_value=None,
                                                        attr_resolve=True)
        node.stage.undo_stack.push(add_attr_cmd)

    def delete_selected_attr(self):
        selected_rows = {item.row() for item in self.selectedItems()}
        if not selected_rows:
            return

        attr_to_del_names = []
        node = None
        for row in selected_rows:
            attrib_name_item: AttrNameTableItem = self.item(row, 0)
            if not node:
                node = attrib_name_item.node_attr.node
            attr_to_del_names.append(attrib_name_item.text())

        del_attr_cmd = commands.DeleteNodeAttributeCommand(stage=node.stage,
                                                           node=node,
                                                           attr_names=attr_to_del_names)
        node.stage.undo_stack.push(del_attr_cmd)

    def copy_selected_attr_path(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        last_row: AttrTableItem = selected_items[-1]
        attr_path = last_row.node_attr.as_path()
        QtWidgets.QApplication.clipboard().setText(attr_path.as_posix())
        LOGGER.info(f"Copied path: {attr_path}")

    def clear_cache_for_selected_attrs(self):
        selected_rows = {item.row() for item in self.selectedItems()}
        for row in selected_rows:
            attrib_name_item: AttrNameTableItem = self.item(row, 0)
            attrib_name_item.node_attr.clear_cache()
            LOGGER.info(f"Cleared cache for: {attrib_name_item.node_attr.as_path()}")
        self.update_node_data()

    def show_context_menu(self, point: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.add_attr_action)
        if self.selectedIndexes():
            menu.addAction(self.copy_selected_attr_path_action)
            menu.addAction(self.delete_selected_attr_action)
            menu.addAction(self.clear_cache_for_selected_action)

        menu.addAction(self.update_action)
        menu.exec_(self.mapToGlobal(point))

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Delete:
            self.delete_selected_attr_action.trigger()
        return super().keyPressEvent(event)
