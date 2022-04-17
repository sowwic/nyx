import typing
from collections import OrderedDict
from PySide2 import QtGui

from nyx.core.serializable import Serializable
from nyx import get_main_logger
if typing.TYPE_CHECKING:
    from nyx.core import Node


LOGGER = get_main_logger()


class Stage(QtGui.QStandardItemModel, Serializable):
    def __init__(self) -> None:
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)
        self.create_connections()

    def create_connections(self):
        self.itemChanged.connect(self.on_node_changed)

    def list_children(self, node: "Node") -> typing.List["Node"]:
        if node is self.invisibleRootItem():
            return [self.invisibleRootItem().child(row) for row in range(self.invisibleRootItem().rowCount())]
        else:
            return node.list_children()

    def add_node(self, node: "Node", parent: "Node" = None):
        if parent is None:
            parent = self.invisibleRootItem()

        parent.appendRow(node)
        LOGGER.debug(f"Added node {node}")

    def delete_node(self, node: "Node"):
        self.beginResetModel()
        parent = node.get_parent()
        self.removeRow(node.row(), parent.index())
        self.endResetModel()

    def on_node_changed(self, node: "Node"):
        node.on_changed()

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        top_nodes = self.list_children(self.invisibleRootItem())
        nodes = [node.serialize() for node in top_nodes]
        data["nodes"] = nodes
        return data

    # TODO: Add implementation
    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)
