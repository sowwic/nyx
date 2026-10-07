import logging
import pathlib
import pprint
import typing
from collections import OrderedDict
from collections.abc import Sequence
from uuid import UUID

from PySide6 import QtCore, QtGui
import shiboken6

from .stage_object import StageObject
from .node import Node, NodeLike
from .node_component import NodeComponent, NodeComponentLike
from .link import Link, LinkLike
from .stage_crawler import StageCrawler
from .plugin_subsystem.registry import NYX_REGISTRY
from .name_validator import NameValidator
from .exceptions import (
    StageObjectQueryError,
    StageObjectRegistrationError,
    StageObjectUnregistrationError,
    NodeComponentLinkError,
)
from ..utils import file_fn
from ..static.vars import ROOT_NODE_PATH
from ..static.enums import CoreNodes

if typing.TYPE_CHECKING:
    from nyx.core.commands import NyxCommand

LOGGER = logging.getLogger(__name__)

type StageObjectLike = NodeLike | NodeComponentLike
TStageObject = typing.TypeVar("TStageObject", bound=Node | NodeComponent | Link)


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
        self.register_node(root_node)

    def create_connections(self):
        self.itemChanged.connect(self.on_node_changed)

    def is_new(self):
        return not self.undo_stack.count() and self.file_path is None

    def is_modified(self):
        if not shiboken6.isValid(self.undo_stack):
            return False
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
        self,
        stage_object: NodeLike | NodeComponentLike | LinkLike,
        expected_type: type[TStageObject] | None = None,
    ) -> TStageObject:
        """Get `nyx` stage object.

        Args:
            stage_object: Input to search object by.

        Returns:
            Found `Node`, `NodeComponent` or `Link` instance or None if not
        """
        original_request = stage_object
        result = None

        if isinstance(stage_object, StageObject):
            result = stage_object

        elif isinstance(stage_object, UUID):
            result = self.uuid_map.get(stage_object)

        elif isinstance(stage_object, pathlib.PurePosixPath):
            getter = (
                self.node_component_from_path
                if stage_object.suffix
                else self.node_from_path
            )
            result = getter(stage_object)

        elif isinstance(stage_object, str):
            try:
                result = self.get_object(UUID(stage_object, version=4))
            except ValueError, AttributeError, TypeError:
                result = self.get_object(pathlib.PurePosixPath(stage_object))

        if result is None:
            raise StageObjectQueryError(
                f"Failed to get object from request: {original_request}"
            )
        if expected_type is not None and not isinstance(result, expected_type):
            raise StageObjectQueryError(
                f"Expected result from {original_request} is of type "
                f"{expected_type.__name__}, got {type(result).__name__} instead"
            )

        return result

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

    def link_components(
        self,
        source_component: NodeComponentLike,
        target_component: NodeComponentLike,
        use_uuid: UUID | str | None = None,
    ) -> Link:
        source_component: NodeComponent = self.get_object(source_component)
        target_component: NodeComponent = self.get_object(target_component)

        if not source_component.produces_output:
            raise NodeComponentLinkError(f"Not readable component: {source_component}")

        if not target_component.accepts_input:
            raise NodeComponentLinkError(f"Not writable component: {source_component}")

        new_link = Link(
            stage=self,
            source=source_component.uuid,
            target=target_component.uuid,
            uuid=use_uuid,
        )
        self.register_link(link=new_link)
        return new_link

    def register_link(self, link: Link):
        if not link.is_valid:
            LOGGER.warning(f"Skipping registration of invalid link: {link}")
            return

        if link.uuid in self._uuid_map and self._uuid_map[link.uuid] is not link:
            raise StageObjectRegistrationError(
                f"Link with UUID {link.uuid} already exists: "
                f"{(self.get_object(link.uuid, expected_type=Link))}"
            )

        self._uuid_map[link.uuid] = link
        source_cpnt: NodeComponent = self.get_object(link.source)
        target_cpnt: NodeComponent = self.get_object(link.target)
        source_cpnt.add_link(link_uuid=link.uuid)
        target_cpnt.add_link(link_uuid=link.uuid)
        LOGGER.debug("Registered link: %s (%s)", str(link), str(link.uuid))

    def unregister_link(self, link: LinkLike):
        link = self.get_object(link)
        self._uuid_map.pop(link.uuid, None)
        source_cpnt: NodeComponent = self.get_object(link.source)
        target_cpnt: NodeComponent = self.get_object(link.target)
        source_cpnt.remove_link(link_uuid=link.uuid)
        target_cpnt.remove_link(link_uuid=link.uuid)

    def collect_links(self, from_node: NodeLike | None = None) -> list[Link]:
        result = []
        from_node = self.get_object(from_node) if from_node else self.root_node
        serialized_node = from_node.serialize()
        for link_data in serialized_node[Node.LINKS_KEY]:
            result.append(self.get_object(link_data[StageObject.UUID_KEY]))
        return result

    def register_node(self, node: Node):
        if node.uuid in self.uuid_map and self.uuid_map[node.uuid] is not node:
            raise StageObjectRegistrationError(
                f"Node with UUID {node.uuid} already exists: "
                f"{(self.get_object(node.uuid).path)}"
            )

        self._uuid_map[node.uuid] = node

        for node_component in node.components_model.list_components():
            if (
                node_component.uuid in self.uuid_map
                and self.uuid_map[node_component.uuid] is not node_component
            ):
                raise StageObjectRegistrationError(
                    f"Component with UUID {node_component.uuid} already exists: "
                    f"{self.get_object(node_component.uuid)}"
                )
            self._uuid_map[node_component.uuid] = node_component

    def unregister_node(self, node: NodeLike):
        if node is self.root_node:
            raise StageObjectUnregistrationError("Can't unregister root node")

        node: Node = self.get_object(node)
        self._uuid_map.pop(node.uuid, None)
        descendant_nodes = node.list_children_tree()
        for component in node.components_model.list_components():
            self._uuid_map.pop(component.uuid)

        for child_node in descendant_nodes:
            self.unregister_node(child_node)
            # self.uuid_map.pop(child_node.uuid, None)

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

    def delete_node(self, nodes: Sequence[NodeLike] | NodeLike) -> None:
        """Delete node from stage.

        Args:
            nodes: nodes to delete.

        """
        if not isinstance(nodes, Sequence):
            nodes = [nodes]
        for node in nodes:
            node = self.get_object(node)
            if node is None:
                raise RuntimeError(f"{self} | Failed to delete node.")

            if node.is_locked:
                raise RuntimeError("Can't delete locked node: %s", node.path)

            # Removed uuids for node, childrent and components
            self.unregister_node(node)

            parent = node.parent()
            self.removeRow(node.row(), parent.index())
            self.node_deleted.emit(node.uuid)

    def on_node_changed(self, node: Node):
        node.on_changed()

    def describe(self) -> str:
        """Pretty format serialized scene.

        Returns:
            str: formatted serialized scene.

        """
        return pprint.pformat(self.root_node.serialize())

    def export_json(self, file_path: pathlib.Path | str) -> None:
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

    def push_command(self, *commands: NyxCommand):
        """Push command to stage's undo stack.
        Also validates command before pushing and raises error if validation fails.

        Args:
            commands (NyxCommand): command to push.
        Raises:
            NyxCommandValidationError: if command validation fails.
        """
        for command in commands:
            if self is not command.stage:
                raise ValueError("Command stage doesn't match current stage.")
            command.validate()

        for command in commands:
            self.undo_stack.push(command)

    def pathify(
        self, stage_object: StageObject | UUID | pathlib.PurePosixPath | str
    ) -> pathlib.PurePosixPath:
        if isinstance(stage_object, pathlib.PurePosixPath):
            return stage_object
        elif isinstance(stage_object, str):
            try:
                uuid = UUID(stage_object)
                return self.get_object(uuid).path
            except Exception:
                return pathlib.PurePosixPath(stage_object)
        elif isinstance(stage_object, StageObject):
            return stage_object.path
        elif isinstance(stage_object, UUID):
            return self.get_object(stage_object).path
