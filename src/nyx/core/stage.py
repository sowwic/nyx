import os
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
    ROOT_ITEM_PATH = path_fn.ROOT_ITEM_PATH

    def __repr__(self) -> str:
        return "Stage"

    def __init__(self) -> None:
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)

        self._path_map: dict[pathlib.PurePosixPath, Node] = {}
        self.undo_stack = QtWidgets.QUndoStack(self)

        self.create_connections()

    @property
    def path_map(self):
        return self._path_map

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
        child_names = {node.text() for node in self.list_top_nodes()}
        if name in child_names:
            index = 1
            while f"{name}{index}" in child_names:
                index += 1
            return name + str(index)
        return name

    def appendRow(self, items: typing.Sequence["Node"]) -> None:
        """Overridden QStandartItemModel method.

        This method will generate a unique path for each item its about to append.

        Args:
            items (typing.Sequence): sequence of nodes.

        Raises:
            ValueError: node path is not unique.
        """

        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            if node.stage:
                LOGGER.warning(f"{node} is already in the stage.")
                continue

            unique_name = self.generate_unique_child_name(node.name)
            new_path = self.ROOT_ITEM_PATH / unique_name
            if new_path in self.path_map:
                LOGGER.error(f"Duplicate path: {new_path}")
                raise ValueError

            # Set unique name and check if path exist
            node.setText(self.generate_unique_child_name(node.name))
            super().appendRow(node)
            LOGGER.debug(f"{self} | Added {node} to root")

            node._cached_path = node.path
            self._path_map[node.path] = node
        return

    def add_node(self, node: "Node | list[Node]", parent: "Node" = None):
        """Adds new node as root node.

        Args:
            node (Node): _description_
        """
        if not isinstance(node, list):
            node = [node]

        for each_node in node:
            if parent:
                parent.appendRow(each_node)
            else:
                self.appendRow(each_node)

    def delete_node(self, node: "Node"):
        """Delete node from stage.

        Args:
            node (Node): node to delete.
        """

        # Removed paths
        self._delete_from_path_map(node)
        self.beginResetModel()
        parent = node.parent() or self.invisibleRootItem()
        self.removeRow(node.row(), parent.index())
        self.endResetModel()

    def _delete_from_path_map(self, node: "Node", children=True):
        """Remove node's path from path map.

        Also handles removal of all children paths.

        Args:
            node (Node): node to remove path for.
            children (bool, optional): delete children paths. Defaults to True.
        """
        self._path_map.pop(node.path)
        if children:
            for child in node.list_children_tree():
                self._path_map.pop(child.path)

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
        """Pretty format serialized scene.

        Returns:
            str: formatted serialized scene.
        """

        return pprint.pformat(self.serialize())

    def export_json(self, file_path: "pathlib.Path | str"):
        """Serialize scene and write it to json file.

        Args:
            file_path (pathlib.Path | str): export file path.
        """
        try:
            file_fn.write_json(file_path, self.serialize(), sort_keys=False)
        except Exception:
            LOGGER.exception("Failed to save stage to file.")

    def import_json(self, file_path: "pathlib.Path | str") -> OrderedDict:
        """Import stage data from json.

        Args:
            file_path (pathlib.Path | str): file to import.

        Returns:
            OrderedDict: imported json data
        """
        try:
            json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        except Exception:
            LOGGER.exception("Failed to load stage from json.")
            return

        self.deserialize(json_data, restore_id=True)
        return json_data

    def get_node_from_relative_path(self, anchor_node: "Node", relative_path: "pathlib.PurePosixPath | str") -> "Node | None":
        """Get node from anchor node and relative to it path.

        If path is invalid will return None.

        top_node

        |- child1

        |--- leaf1

        |- child2

        |--- leaf2

        leaf1 -> leaf2 path: ../../child2/leaf2
        child1 -> leaf1 path: ./leaf1
        child1 -> child2 path: ../child2

        Args:
            anchor_node (Node): node for find start search from.
            relative_path (pathlib.PurePosixPath | str): relative path.

        Returns:
            _type_: _description_
        """
        try:
            absolute_path = path_fn.get_absolute_path_from_relative(anchor_node.path, relative_path)
        except IndexError:
            LOGGER.warning(f"Invalid path: {relative_path}")
            return None
        except Exception:
            LOGGER.error(f"Failed to get absolute path from: {anchor_node.path}, {relative_path}")
            raise

        return self.path_map.get(absolute_path)

    def get_relative_path_to(self, from_node: "Node", to_node: "Node"):
        """Get relative path between nodes.

        Args:
            from_node (Node): From this node.
            to_node (Node): To this node.

        Returns:
            pathlib.PurePosixPath: relative path
        """
        path_str = os.path.relpath(to_node.path.as_posix(), from_node.path.as_posix())
        path_str = path_str.replace(os.sep, "/")
        return pathlib.PurePosixPath(path_str)

    def get_node_children_from_path(self, node_path: "pathlib.PurePosixPath | str") -> "list[Node]":
        """Get children of node with given full path.

        Args:
            node_path (pathlib.PurePosixPath | str): full node path.

        Returns:
            _type_: _description_
        """
        if not isinstance(node_path, pathlib.PurePosixPath):
            node_path = pathlib.PurePosixPath(node_path)

        if node_path == pathlib.PurePosixPath("/"):
            return self.list_top_nodes()

        if node_path not in self.path_map:
            LOGGER.warning(f"Can't get children of node with given path: {node_path}")
            return []

        return self.path_map[node_path].list_children()
