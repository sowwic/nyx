import logging
import pathlib
import pprint
import typing
from collections import OrderedDict
from collections.abc import Sequence

from PySide6 import QtCore, QtGui

from nyx.core import Node
from nyx.core.path_resolver import StagePathResolver
from nyx.core.stage_handler import StageHandler
from nyx.utils import file_fn

if typing.TYPE_CHECKING:
    from nyx.core.commands import NyxCommand

LOGGER = logging.getLogger(__name__)


class Stage(QtGui.QStandardItemModel):
    FILE_EXTENSION = ".nyx"
    ROOT_NODE_PATH = pathlib.PosixPath("/stage")

    node_deleted = QtCore.Signal(pathlib.PurePosixPath)

    def __repr__(self) -> str:
        return f"Stage <Nodes: {self.total_node_count()} | File: {self.file_path}>"

    def __truediv__(self, other: str) -> pathlib.PurePosixPath:
        if isinstance(other, str):
            return self.ROOT_NODE_PATH / other
        return NotImplemented

    def __init__(self) -> None:
        super().__init__()
        self.last_saved_undo_index = 0
        self.file_path: pathlib.Path | None = None
        self._path_map: dict[pathlib.PurePosixPath, Node] = {}
        self._path_resolver = StagePathResolver()
        self._handler = StageHandler(self)
        self.undo_stack = QtGui.QUndoStack(self)
        self._create_root_node()

        self.create_connections()

    @property
    def path_map(self) -> dict[pathlib.PurePosixPath, Node]:
        return self._path_map

    @property
    def handler(self) -> StageHandler:
        return self._handler

    @property
    def path_resolver(self) -> StagePathResolver:
        return self._path_resolver

    def _create_root_node(self):
        root_node = Node(name="stage")
        self.appendRow(root_node)

    def create_connections(self):
        self.itemChanged.connect(self.on_node_changed)

    def is_new(self):
        return not self.undo_stack.count() and self.file_path is None

    def is_modified(self):
        return (
            self.file_path is None
            or self.last_saved_undo_index != self.undo_stack.index()
        )

    def total_node_count(self) -> int:
        """Get total number of nodes in the stage.

        Returns:
            int: number of nodes in the stage.
        """

        def count_parent(parent_index: QtCore.QModelIndex):
            """Count children of given parent index.

            Args:
                parent_index (QModelIndex): parent index

            Returns:
                int: number of child nodes
            """
            total = 0
            rows = self.rowCount(parent_index)
            for row in range(rows):
                index = self.index(row, 0, parent_index)
                total += 1
                total += count_parent(index)
            return total

        return count_parent(self.root_node.index())

    def list_children(self, node: Node) -> list[Node]:
        """List children of given node.

        Args:
            node (Node): node to list children of

        Returns:
            list[Node]: list of child nodes
        """
        node = node or self.invisibleRootItem()
        if node is self.invisibleRootItem():
            return [
                self.invisibleRootItem().child(row)
                for row in range(self.invisibleRootItem().rowCount())
            ]
        else:
            return node.list_children()

    def list_top_nodes(self) -> list[Node]:
        return self.list_children(self.root_node)

    def list_top_nodes_paths(self) -> list[pathlib.PurePosixPath]:
        return [node.cached_path for node in self.list_top_nodes()]

    def is_top_node_path(self, path: str | pathlib.PurePosixPath) -> bool:
        if isinstance(path, str):
            path = pathlib.PosixPath(path)
        return path in set(self.list_top_nodes_paths())

    @property
    def root_node(self) -> Node:
        return self.node(self.ROOT_NODE_PATH)

    def generate_unique_node_name(
        self,
        base_name: str,
        parent_node: Node | pathlib.PurePosixPath | str | None = None,
    ):
        if parent_node:
            parent_node = self.node(parent_node)
            parent_path = parent_node.path
        else:
            parent_path = self.ROOT_NODE_PATH

        new_node_path = parent_path / base_name
        if new_node_path in self.path_map:
            index = 1
            while parent_path / f"{base_name}{index}" in self.path_map:
                index += 1
            return f"{base_name}{index}"
        return base_name

    def appendRow(self, items: typing.Sequence[Node]) -> None:
        """Overridden QStandardItemModel method.

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

            unique_name = self.generate_unique_node_name(
                node.name, parent_node=node.parent()
            )
            new_path = self.ROOT_NODE_PATH / unique_name
            if new_path in self.path_map:
                LOGGER.error(f"Duplicate path: {new_path}")
                raise ValueError

            # Set unique name and check if path exist
            node.setText(unique_name)
            super().appendRow(node)

            node.cache_current_path()
            self._path_map[node.cached_path] = node
            LOGGER.debug(f"{self} | Added {node} to root")

    def node(self, node: Node | pathlib.PurePosixPath | str | None) -> Node:
        """Get node instance.

        Args:
            node (Node | pathlib.PurePosixPath | str | None): node or full path.

        Returns:
            Node | None: node instance if found

        """
        if node is None:
            return node
        if isinstance(node, Node):
            return node
        elif isinstance(node, pathlib.PurePosixPath):
            return self.path_map.get(node)
        elif isinstance(node, str):
            return self.path_map.get(pathlib.PurePosixPath(node))
        else:
            LOGGER.exception(f"{self} | Invalid argument type: {type(node)}")
            return None

    def add_node(
        self,
        node: Node | list[Node],
        parent: Node | pathlib.PurePosixPath | str | None = None,
    ):
        """Adds new node as root node.

        Args:
            node (Node): _description_

        """
        if not isinstance(node, list):
            node = [node]

        if parent is not None:
            parent = self.node(parent)
        else:
            parent = self.root_node

        for each_node in node:
            parent.appendRow(each_node)

    def delete_node(self, nodes: Sequence[Node | pathlib.PurePosixPath | str]):
        """Delete node from stage.

        Args:
            node (Node): node to delete.

        """
        if isinstance(nodes, (Node, str, pathlib.PurePosixPath)):
            nodes = [nodes]
        for node in nodes:
            node = self.node(node)
            if node is None:
                LOGGER.exception(f"{self} | Failed to delete node.", stack_info=True)
                return

            # Removed paths
            node = self.node(node)
            node_path_to_emit = node.path
            self._delete_from_path_map(node)
            parent = node.parent()
            self.removeRow(node.row(), parent.index())
            self.node_deleted.emit(node_path_to_emit)

    def _delete_from_path_map(self, node: Node, children=True):
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

    def on_node_changed(self, node: Node):
        node.on_changed()

    def describe(self):
        """Pretty format serialized scene.

        Returns:
            str: formatted serialized scene.

        """
        return pprint.pformat(self.root_node.serialize())

    def export_json(self, file_path: pathlib.Path | str):
        """Serialize scene and write it to json file.

        Args:
            file_path (pathlib.Path | str): export file path.

        """
        try:
            file_fn.write_json(file_path, self.root_node.serialize(), sort_keys=False)
            self.file_path = pathlib.Path(file_path)
            self.last_saved_undo_index = self.undo_stack.index()
            LOGGER.info(f"Exported stage: {self.file_path}")
        except Exception:
            LOGGER.exception("Failed to save stage to file.")

    def import_json(self, file_path: pathlib.Path | str) -> OrderedDict:
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

        self.root_node.deserialize(json_data)
        self.file_path = pathlib.Path(file_path)
        self.last_saved_undo_index = self.undo_stack.index()
        LOGGER.info(f"Imported stage: {self.file_path}")
        return json_data

    def get_node_children_from_path(
        self, node_path: pathlib.PurePosixPath | str
    ) -> list[Node]:
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

    def execute_node_from_path(self, path):
        node = self.node(path)
        node.execute()

    def push_command(self, command: NyxCommand):
        """Push command to stage's undo stack.
        Also validates command before pushing and raises error if validation fails.

        Args:
            command (NyxCommand): command to push.
        Raises:
            NyxCommandValidationError: if command validation fails.
        """
        if self is not command.stage:
            raise ValueError("Command stage doesn't match current stage.")

        command.validate()
        self.undo_stack.push(command)

    def pathify(self, node: Node | pathlib.PurePosixPath | str) -> pathlib.PurePosixPath:
        """Convert object to path.

        Args:
            node (Node | pathlib.PurePosixPath | str): node to convert

        Raises:
            TypeError: Invalid object type

        Returns:
            pathlib.PurePosixPath: node as path
        """
        if isinstance(node, Node):
            return node.cached_path
        elif isinstance(node, (str, pathlib.PurePosixPath)):
            return pathlib.PurePosixPath(node)
        else:
            raise TypeError(f"Unable to pathify {node}")
