import typing
import pprint
import pathlib
from collections import OrderedDict, Sequence
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core.serializable import Serializable
from nyx.utils import file_fn
from nyx.core import Node
from nyx.core.stage_executor import StageExecutor


LOGGER = get_main_logger()


class Stage(QtGui.QStandardItemModel, Serializable):

    node_deleted = QtCore.Signal(pathlib.PurePosixPath)

    FILE_EXTENSION = ".nyx"
    ROOT_ITEM_PATH = pathlib.PurePosixPath("/")

    def __repr__(self) -> str:
        return "Stage"

    def __init__(self) -> None:
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)
        self.last_saved_undo_index = 0
        self.file_path: pathlib.Path = None
        self._path_map: dict[pathlib.PurePosixPath, Node] = {}
        self.__execution_start_path: pathlib.PurePosixPath = None
        self.__executor = StageExecutor(self)
        self.undo_stack = QtWidgets.QUndoStack(self)

        self.create_connections()

    @property
    def path_map(self):
        return self._path_map

    @property
    def executor(self):
        return self.__executor

    @property
    def execution_start_path(self):
        return self.__execution_start_path

    def create_connections(self):
        self.itemChanged.connect(self.on_node_changed)

    def is_new(self):
        return not self.undo_stack.count() and self.file_path is None

    def is_modified(self):
        return self.file_path is None or self.last_saved_undo_index != self.undo_stack.index()

    def list_children(self, node: "Node") -> typing.List["Node"]:
        node = node or self.invisibleRootItem()
        if node is self.invisibleRootItem():
            return [self.invisibleRootItem().child(row) for row in range(self.invisibleRootItem().rowCount())]
        else:
            return node.list_children()

    def list_top_nodes(self) -> "list[Node]":
        return self.list_children(self.invisibleRootItem())

    def list_top_nodes_paths(self) -> "list[pathlib.PurePosixPath]":
        return [node.cached_path for node in self.list_top_nodes()]

    def is_top_node_path(self, path: "str | pathlib.PurePosixPath") -> bool:
        if isinstance(path, str):
            path = pathlib.PosixPath(path)
        return path in set(self.list_top_nodes_paths())

    def generate_unique_node_name(self, base_name: str,
                                  parent_node: "Node | pathlib.PurePosixPath | str" = None):
        if parent_node:
            parent_node = self.node(parent_node)
            parent_path = parent_node.path
        else:
            parent_path = self.ROOT_ITEM_PATH

        new_node_path = parent_path / base_name
        if new_node_path in self.path_map:
            index = 1
            while parent_path / f"{base_name}{index}" in self.path_map:
                index += 1
            return base_name + str(index)
        return base_name

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

            unique_name = self.generate_unique_node_name(node.name, parent_node=node.parent())
            new_path = self.ROOT_ITEM_PATH / unique_name
            if new_path in self.path_map:
                LOGGER.error(f"Duplicate path: {new_path}")
                raise ValueError

            # Set unique name and check if path exist
            node.setText(unique_name)
            super().appendRow(node)
            LOGGER.debug(f"{self} | Added {node} to root")

            node.cache_current_path()
            self._path_map[node.cached_path] = node

    def node(self, node):
        if node is None:
            return None
        if isinstance(node, Node):
            return node
        elif isinstance(node, pathlib.PurePosixPath):
            return self.path_map.get(node)
        elif isinstance(node, str):
            return self.path_map.get(pathlib.PurePosixPath(node))
        else:
            LOGGER.exception(f"{self} | Invalid argument type: {type(node)}")
            return None

    def add_node(self, node: "Node | list[Node]", parent: "Node | pathlib.PurePosixPath | str" = None):
        """Adds new node as root node.

        Args:
            node (Node): _description_
        """
        if not isinstance(node, list):
            node = [node]

        if parent is not None:
            parent = self.node(parent)

        for each_node in node:
            if parent:
                parent.appendRow(each_node)
            else:
                self.appendRow(each_node)

    def delete_node(self, nodes: "Sequence[Node | pathlib.PurePosixPath | str]"):
        """Delete node from stage.

        Args:
            node (Node): node to delete.
        """
        if isinstance(nodes, (Node, str, pathlib.PurePosixPath)):
            nodes = [nodes]
        for node in nodes:
            node = self.node(node)
            if node is None:
                LOGGER.exception(f"{self} | Failed to delete node.")
                return

            # Removed paths
            node = self.node(node)
            node_path_to_emit = node.path
            self._delete_from_path_map(node)
            self.beginResetModel()
            parent = node.parent() or self.invisibleRootItem()
            self.removeRow(node.row(), parent.index())
            self.endResetModel()
            self.node_deleted.emit(node_path_to_emit)

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
        data["execution_start_path"] = self.get_execution_start_path(None, serializable=True)
        return data

    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)
        # Deserialize nodes
        for top_node_data in data.get("nodes", {}):
            top_node = Node()
            self.add_node(top_node)
            top_node.deserialize(top_node_data, hashmap, restore_id=True)
        # Extra data
        self.set_execution_start_path(None, data.get("execution_start_path"))

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
            self.file_path = pathlib.Path(file_path)
            self.last_saved_undo_index = self.undo_stack.index()
            LOGGER.info(f"Exported stage: {self.file_path}")
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
        self.file_path = pathlib.Path(file_path)
        self.last_saved_undo_index = self.undo_stack.index()
        LOGGER.info(f"Imported stage: {self.file_path}")
        return json_data

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

    def set_stage_execution_start_path(self, start_path: "Node | pathlib.PurePosixPath | str"):
        """Set execution start path for this stage.

        Args:
            start_path (Node | pathlib.PurePosixPath | str): node path.
        """
        if not (isinstance(start_path, pathlib.PurePosixPath) or start_path is None):
            if isinstance(start_path, Node):
                start_path = start_path.cached_path
            elif isinstance(start_path, str):
                start_path = pathlib.PurePosixPath(start_path)
            elif start_path is None:
                pass
            else:
                LOGGER.exception(f"{self} | Invalid execution start path object: {start_path}")
                return

        self.__execution_start_path = start_path
        LOGGER.info(f"{self} | Set execution start path to {start_path}")

    def set_execution_start_path(self,
                                 for_node: "Node | pathlib.PurePosixPath | str",
                                 start_path: "Node | pathlib.PurePosixPath | str"):
        """Utility method for setting execution for either stage or node.

        Args:
            for_node (Node | pathlib.PurePosixPath | str): set execution path for this node. If None - path will be set for stage.
            start_path (Node | pathlib.PurePosixPath | str): new execution start path.
        """
        if not isinstance(start_path, pathlib.PurePosixPath):
            if isinstance(start_path, Node):
                start_path = start_path.cached_path
            elif isinstance(start_path, str):
                start_path = pathlib.PurePosixPath(start_path)
            elif start_path is None:
                pass
            else:
                LOGGER.exception(f"{self} | Invalid execution start path object: {start_path}")
                return

        if for_node is None:
            self.set_stage_execution_start_path(start_path)  # Set path for stage if node is None
            return

        if not isinstance(for_node, Node):
            if isinstance(for_node, (str, pathlib.PurePosixPath)):
                for_node = self.node(for_node)
            else:
                LOGGER.exception(f"{self} | Invalid argument type for_node: {for_node}")
                return

        for_node.set_execution_start_path(start_path)

    def get_execution_start_path(self,
                                 for_node: "Node | str | pathlib.PurePosixPath | None",
                                 serializable=False
                                 ) -> "pathlib.PurePosixPath | str | None":
        """Get execution start path for stage or node.

        Args:
            for_node (Node | str | pathlib.PurePosixPath | None): Object to get start execution path for. None will get stage's path.
            serializable (bool, optional): get resulting path in jsonable form. Defaults to False.

        Returns:
            : _description_
        """
        original_for_node = for_node
        if for_node is None:
            path = self.execution_start_path
            if serializable and isinstance(path, pathlib.PurePosixPath):
                path = path.as_posix()
            return path

        elif not isinstance(for_node, Node):
            if isinstance(for_node, (str, pathlib.PurePosixPath)):
                for_node = self.node(for_node)
            else:
                LOGGER.exception(f"{self} | Invalid execution start path object: {for_node}")
                return

        if not isinstance(for_node, Node):
            LOGGER.exception(f"{self} | Failed to execution start path from {original_for_node}")
            return

        return for_node.get_execution_start_path(serializable=serializable)

    def execute_node_from_path(self, path):
        node = self.node(path)
        node.execute()
