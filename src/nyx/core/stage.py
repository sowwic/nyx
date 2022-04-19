import typing
import pprint
import pathlib
from collections import OrderedDict
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core.serializable import Serializable
from nyx.utils import file_fn
from nyx.utils import path_fn
from nyx.core import Node


LOGGER = get_main_logger()


class Stage(QtGui.QStandardItemModel, Serializable):

    FILE_EXTENSION = ".nyx"

    def __init__(self) -> None:
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)

        self.path_map = {}
        self.undo_stack = QtWidgets.QUndoStack(self)

        self.create_connections()

    def create_connections(self):
        self.itemChanged.connect(self.on_node_changed)

    def list_children(self, node: "Node") -> typing.List["Node"]:
        if node is self.invisibleRootItem():
            return [self.invisibleRootItem().child(row) for row in range(self.invisibleRootItem().rowCount())]
        else:
            return node.list_children()

    def list_top_nodes(self) -> "list[Node]":
        return self.list_children(self.invisibleRootItem())

    def generate_unique_child_name(self, name: str):
        child_names = {node.text() for node in self.list_children(self.invisibleRootItem())}
        if name in child_names:
            index = 1
            while f"{name}{index}" in child_names:
                index += 1
            return name + str(index)
        return name

    def appendRow(self, items: typing.Sequence) -> None:
        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            node.setText(self.generate_unique_child_name(node.name))
            super().appendRow(node)
            if node.path in self.path_map:
                LOGGER.error(f"Duplicate path: {node.path}")
                raise ValueError

            node._cached_path = node.path
            self.path_map[node.path] = node
        return

    def add_node(self, node: "Node"):
        self.appendRow(node)
        LOGGER.debug(f"Added {node} to root")

    def delete_node(self, node: "Node"):
        # Removed paths
        self._delete_from_path_map(node)
        self.beginResetModel()
        parent = node.parent() or self.invisibleRootItem()
        self.removeRow(node.row(), parent.index())
        self.endResetModel()

    def _delete_from_path_map(self, node: "Node", children=True):
        self.path_map.pop(node.path)
        if children:
            for child in node.list_children_tree():
                self.path_map.pop(child.path)

    def on_node_changed(self, node: "Node"):
        node.on_changed()

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        top_nodes = self.list_top_nodes()
        nodes = [node.serialize() for node in top_nodes]
        data["nodes"] = nodes
        return data

    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)
        for top_node_data in data.get("nodes", {}):
            top_node = Node()
            self.add_node(top_node)
            top_node.deserialize(top_node_data, hashmap, restore_id=True)

    def describe(self):
        return pprint.pformat(self.serialize())

    def export_json(self, file_path):
        try:
            file_fn.write_json(file_path, self.serialize(), sort_keys=False)
        except Exception:
            LOGGER.exception("Failed to save stage to file.")

    def import_json(self, file_path):
        try:
            json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        except Exception:
            LOGGER.exception("Failed to load stage from json.")
            return

        self.deserialize(json_data, restore_id=True)
        return json_data

    def get_node_from_relative_path(self, anchor_node: "Node", relative_path: pathlib.PurePosixPath):
        try:
            absolute_path = path_fn.get_absolute_path_from_relative(anchor_node.path, relative_path)
        except IndexError:
            LOGGER.warning(f"Invalid path: {relative_path}")
            return None
        except Exception:
            LOGGER.error(f"Failed to get absolute path from: {anchor_node.path}, {relative_path}")
            raise

        return self.path_map.get(absolute_path)
