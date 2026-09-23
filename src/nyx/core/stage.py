import logging
import pathlib
import pprint
import typing
from collections import OrderedDict
from collections.abc import Sequence
from uuid import UUID

from PySide6 import QtCore, QtGui

from .stage_object import StageObject
from .node import Node, NodeLike
from .node_component import NodeComponent, NodeComponentLike
from .stage_crawler import StageCrawler
from .plugin_subsystem.registry import NYX_REGISTRY
from .name_validator import NameValidator
from ..utils import file_fn
from ..static.vars import ROOT_NODE_PATH
from ..static.enums import CoreNodes

if typing.TYPE_CHECKING:
    from nyx.core.commands import NyxCommand

LOGGER = logging.getLogger(__name__)

type StageObjectLike = NodeLike | NodeComponentLike


class Stage(QtGui.QStandardItemModel):
    FILE_EXTENSION = ".nyx"

    node_deleted = QtCore.Signal(UUID)

    def __repr__(self) -> str:
        return f"Stage <Nodes: {self.total_node_count()} | File: {self.file_path}>"

    def __truediv__(self, other: str) -> pathlib.PurePosixPath:
        if isinstance(other, str):
            return self.root_node.path / other
        raise NotImplementedError

    def __init__(self) -> None:
        super().__init__()
        self.last_saved_undo_index = 0
        self.file_path: pathlib.Path | None = None
        self._uuid_map: dict[UUID, Node] = {}
        self._crawler = StageCrawler(self)
        self.undo_stack = QtGui.QUndoStack(self)
        self._create_root_node()

        self.create_connections()

    @property
    def uuid_map(self) -> dict[UUID, Node]:
        return self._uuid_map

    @property
    def crawler(self) -> StageCrawler:
        return self._crawler

    def create_node(
        self, type_id: str, name: str | None = None, uuid: UUID | str | None = None
    ) -> Node:
        node_cls = NYX_REGISTRY.get_node_cls(type_id=type_id)
        node = node_cls(name=name, uuid=uuid, parent=None)
        return node

    def _create_root_node(self):
        root_node = self.create_node(type_id=CoreNodes.EMPTY, name=ROOT_NODE_PATH.name)
        root_node.is_locked = True
        self.appendRow(root_node)
        self.uuid_map[root_node.uuid] = root_node

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
        node = node or self.root_node
        return node.list_children()

    @property
    def root_node(self) -> Node:
        return self.get_object(ROOT_NODE_PATH)

    def generate_unique_node_name(
        self,
        base_name: str,
        parent_node: NodeLike | None = None,
    ):
        base_name = NameValidator.get_valid_stage_object_name(base_name)
        parent_node: Node = (
            self.get_object(parent_node) if parent_node else self.root_node
        )
        existing_children_names: set[str] = parent_node.child_names_set
        if base_name not in existing_children_names:
            return base_name

        index = 1
        result_name = base_name
        while result_name in existing_children_names:
            result_name = f"{base_name}{index}"
            index += 1
        return result_name

    def filter_top_level_nodes(self, nodes: list[NodeLike]) -> list[Node]:
        nodes: list[Node] = [self.get_object(node) for node in nodes]
        paths_set = {node.path for node in nodes}
        return [
            node for node in nodes if not set(node.path.parents).intersection(paths_set)
        ]

    def get_object(
        self, stage_object: NodeLike | NodeComponentLike | None
    ) -> Node | NodeComponent | None:
        if stage_object is None:
            return None

        if isinstance(stage_object, StageObject):
            return stage_object

        if isinstance(stage_object, UUID):
            return self.uuid_map[stage_object]

        if isinstance(stage_object, str):
            try:
                return self.get_object(UUID(stage_object, version=4))
            except (ValueError, AttributeError, TypeError):
                stage_object = pathlib.Path(stage_object)

        if isinstance(stage_object, pathlib.PurePosixPath):
            getter = (
                self.node_component_from_path
                if stage_object.suffix
                else self.node_from_path
            )
            try:
                return getter(stage_object)
            except Exception:
                return None

        return None

    def node_from_path(self, path: pathlib.PurePosixPath | str) -> Node | None:
        path = pathlib.PurePosixPath(path)
        if path == ROOT_NODE_PATH:
            return self.item(0)

        segments = path.parts[1:]  # drop the leading "/"
        if not segments or segments[0] != ROOT_NODE_PATH.name:
            return None

        current = self.root_node
        for name in segments[1:]:
            current = current.find_child_by_name(name)
            if current is None:
                return None
        return current

    def node_component_from_path(
        self, path: pathlib.PurePosixPath | str
    ) -> NodeComponent | None:
        path = pathlib.PurePosixPath(path)
        component_name = path.suffix
        if not component_name:
            raise ValueError(f"Not valid component path: {path}")

        node_path = path.with_suffix("")
        node = self.get_object(node_path)
        if not node:
            raise ValueError(f"Node for given component path doesn't exist: {path}")

        return node.components_model.get_component(component_name)

    def add_node(
        self,
        node: Node | list[Node],
        parent: NodeLike | None = None,
    ):
        """Adds new node as root node.

        Args:
            node (Node): _description_

        """
        if not isinstance(node, list):
            node = [node]

        parent: Node = self.get_object(parent) if parent else self.root_node

        for each_node in node:
            parent.appendRow(each_node)

    def delete_node(self, nodes: Sequence[NodeLike] | NodeLike):
        """Delete node from stage.

        Args:
            node (Node): node to delete.

        """
        if not isinstance(nodes, Sequence):
            nodes = [nodes]
        for node in nodes:
            node = self.get_object(node)
            if node is None:
                raise RuntimeError(f"{self} | Failed to delete node.")

            if node.is_locked:
                raise RuntimeError("Can't delete locked node: %s", node.path)

            # Removed paths
            self._delete_from_uuid_map(node)
            parent = node.parent()
            self.removeRow(node.row(), parent.index())
            self.node_deleted.emit(node.uuid)

    def _delete_from_uuid_map(self, node: Node):
        self.uuid_map.pop(node.uuid)
        descendant_nodes = node.list_children_tree()
        for child_node in descendant_nodes:
            self.uuid_map.pop(child_node.uuid)

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
            serialized_data = self.root_node.serialize()
            file_fn.write_json(file_path, serialized_data, sort_keys=False)
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

        Node.deserialize(serialized_node=json_data, node=self.root_node)
        self.file_path = pathlib.Path(file_path)
        self.last_saved_undo_index = self.undo_stack.index()
        LOGGER.info(f"Imported stage: {self.file_path}")
        return json_data

    def execute_node_from_path(self, path):
        node = self.node_from_path(path)
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

    def pathify(self, stage_object: StageObject | UUID | pathlib.PurePosixPath | str):
        if isinstance(stage_object, pathlib.PurePosixPath):
            return stage_object
        elif isinstance(stage_object, str):
            try:
                uuid = UUID(stage_object)
                return self.get_object(uuid)
            except Exception:
                return pathlib.PurePosixPath(stage_object)
        elif isinstance(stage_object, StageObject):
            return stage_object.path
        elif isinstance(stage_object, UUID):
            return self.get_object(stage_object)
