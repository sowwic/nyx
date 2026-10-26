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
from ..utils import file_fn, names_fn
from ..static.vars import ROOT_NODE_PATH
from ..static.enums import CoreNodes

if typing.TYPE_CHECKING:
    from nyx.core.commands import NyxCommand
    from nyx.core.util_object import UtilObject

LOGGER = logging.getLogger(__name__)

type StageObjectLike = NodeLike | NodeComponentLike
TStageObject = typing.TypeVar("TStageObject", bound=Node | NodeComponent | Link)


class Stage(QtGui.QStandardItemModel):
    """Item model holding a tree of nodes, their undo stack and the uuid registry.

    Attributes:
        file_path: file the stage was loaded from or saved to
        undo_stack: undo stack for commands operating on the stage
        node_deleted: emitted with the uuid of a deleted node
    """

    FILE_EXTENSION = ".nyx"

    node_deleted = QtCore.Signal(UUID)
    execution_started = QtCore.Signal()
    execution_finished = QtCore.Signal()
    execution_succeeded = QtCore.Signal()
    execution_failed = QtCore.Signal(Node)

    def __repr__(self) -> str:
        """str: node count and file path."""
        return f"Stage <Nodes: {self.total_node_count()} | File: {self.file_path}>"

    def __truediv__(self, other: typing.Any) -> pathlib.PurePosixPath:
        """Build a path under the root node.

        Args:
            other (str): path segment to append.

        Returns:
            pathlib.PurePosixPath: root node path joined with the segment.

        Raises:
            NotImplementedError: if other isn't a string.
        """
        if isinstance(other, str):
            return self.root_node.path / other
        raise NotImplementedError

    def __init__(self) -> None:
        """Initialize Stage with a root node and an empty undo stack."""
        super().__init__()
        self.last_saved_undo_index = 0
        self.file_path: pathlib.Path | None = None
        self._uuid_map: dict[UUID, Node] = {}
        self._crawler = StageCrawler(self)
        self.undo_stack = QtGui.QUndoStack(self)
        self._create_root_node()
        self._register_qml_role_names()

        self.create_connections()

    def __del__(self) -> None:
        """Clear the undo stack while the python objects are still valid."""
        # Commands keep Python state alive; empty the undo stack while the Python
        # objects are still intact. Letting the C++ destructor clear it during
        # garbage collection can crash, since the commands' wrappers may be gone.
        try:
            if shiboken6.isValid(self) and shiboken6.isValid(self.undo_stack):
                # Silent: listeners (e.g. graph editors) may already be deleted.
                self.undo_stack.blockSignals(True)
                self.undo_stack.clear()
        except Exception:  # noqa: BLE001 - never raise from a finalizer
            pass

    @property
    def uuid_map(self) -> dict[UUID, Node]:
        """dict[UUID, Node]: registered stage objects by uuid."""
        return self._uuid_map

    @property
    def crawler(self) -> StageCrawler:
        """StageCrawler: crawler used to execute the stage."""
        return self._crawler

    def _register_qml_role_names(self) -> None:
        """Expose Node roles to QML by name."""
        names = dict(self.roleNames())
        names.update(names_fn.enum_to_dict(Node.Roles))  # ty: ignore
        self.setItemRoleNames(names)

    def create_node(
        self, type_id: str, name: str | None = None, uuid: UUID | str | None = None
    ) -> Node:
        """Instantiate a registered node type without adding it to the stage.

        Args:
            type_id (str): registered node type id.
            name (str | None): node name.
            uuid (UUID | str | None): node uuid.

        Returns:
            Node: new node.
        """
        node_cls = NYX_REGISTRY.get_node_cls(type_id=type_id)
        node = node_cls(name=name, uuid=uuid, parent=None)
        return node

    def _create_root_node(self):
        """Create and register the locked root node."""
        root_node = self.create_node(type_id=CoreNodes.EMPTY, name=ROOT_NODE_PATH.name)
        root_node.is_locked = True
        self.appendRow(root_node)
        self.register_node(root_node)

    def create_connections(self):
        """Connect model signals."""
        self.itemChanged.connect(self.on_node_changed)

    def is_new(self):
        """bool: stage is untouched and was never saved."""
        return not self.undo_stack.count() and self.file_path is None

    def clear_undo_history(self) -> None:
        """Forget the undo history, for changes the undo stack can't describe.

        The stage counts as modified afterwards: it no longer matches its file.
        """
        self.undo_stack.clear()
        self.last_saved_undo_index = -1

    def is_modified(self):
        """bool: stage has unsaved changes."""
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
        """Node: root node of the stage."""
        return self.get_object(ROOT_NODE_PATH)

    def generate_unique_node_name(
        self,
        base_name: str,
        parent_node: NodeLike | None = None,
    ):
        """Generate a node name not used by the siblings under a parent.

        Args:
            base_name (str): preferred name.
            parent_node (NodeLike | None): parent node. Defaults to the root node.

        Returns:
            str: unique valid node name.
        """
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
        """Drop nodes that have an ancestor in the given nodes.

        Args:
            nodes (list[NodeLike]): nodes to filter.

        Returns:
            list[Node]: nodes without ancestors in the input.
        """
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
        """Find a node by path.

        Args:
            path (pathlib.PurePosixPath | str): node path.

        Returns:
            Node | None: node, None if the path doesn't exist.
        """
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
        """Find a node component by path.

        Args:
            path (pathlib.PurePosixPath | str): component path.

        Returns:
            NodeComponent | None: component, None if the node has no such component.

        Raises:
            ValueError: if the path isn't a component path or its node doesn't exist.
        """
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
        """Link two components and register the link.

        Args:
            source_component (NodeComponentLike): component providing output.
            target_component (NodeComponentLike): component accepting input.
            use_uuid (UUID | str | None): uuid for the link. Generated if omitted.

        Returns:
            Link: created link.

        Raises:
            NodeComponentLinkError: if the components can't be linked.
        """
        source_component: NodeComponent = self.get_object(source_component)
        target_component: NodeComponent = self.get_object(target_component)

        if not source_component.readable:
            raise NodeComponentLinkError(f"Not readable component: {source_component}")

        if not target_component.writable:
            raise NodeComponentLinkError(f"Not writable component: {target_component}")

        if not target_component.accepts_datatype_of(source_component):
            raise NodeComponentLinkError(
                f"Incompatible datatypes: {source_component.datatype.display_name} "
                f"to {target_component.datatype.display_name}"
            )

        if source_component.single_output and source_component.output_links:
            raise NodeComponentLinkError(
                f"Component allows a single output link: {source_component}"
            )

        if self.would_link_create_cycle(source_component, target_component):
            raise NodeComponentLinkError(
                f"Link would create a cycle between nodes: {source_component} "
                f"to {target_component}"
            )

        new_link = Link(
            stage=self,
            source=source_component.uuid,
            target=target_component.uuid,
            uuid=use_uuid,
        )
        self.register_link(link=new_link)
        return new_link

    def would_link_create_cycle(
        self, source_component: NodeComponent, target_component: NodeComponent
    ) -> bool:
        """Check whether a link would make values depend on themselves.

        Between two nodes the nodes are looked at, not the components: nodes can't take
        values from each other in both directions, whatever components the links are
        between. Inside of a node only the components count, they can be linked to
        each other as long as the values don't loop back. Flow links count too, loops
        are made with loop nodes that run their body, not with circular links.

        Args:
            source_component (NodeComponent): component providing output.
            target_component (NodeComponent): component accepting input.

        Returns:
            bool: the source already depends on the target (the node of the source on
                the node of the target), or both are the same component.
        """
        if source_component is target_component:
            return True

        if source_component.node is target_component.node:
            start, goal = target_component, source_component
            next_of = self._find_dependent_components
        else:
            start, goal = target_component.node, source_component.node
            next_of = self._find_dependent_nodes

        pending = [start]
        reached = {start.uuid}
        while pending:
            item = pending.pop()
            if item is goal:
                return True
            for next_item in next_of(item):
                if next_item.uuid not in reached:
                    reached.add(next_item.uuid)
                    pending.append(next_item)
        return False

    @staticmethod
    def _find_dependent_components(component: NodeComponent) -> list[NodeComponent]:
        """Find the components that take their value from a component.

        Args:
            component (NodeComponent): component providing the value.

        Returns:
            list[NodeComponent]: targets of its output links.
        """
        return [link.target_component for link in component.output_links]

    @staticmethod
    def _find_dependent_nodes(node: Node) -> list[Node]:
        """Find the nodes that take values from a node.

        Args:
            node (Node): node providing the values.

        Returns:
            list[Node]: nodes with a component linked to a component of the node.
        """
        return [
            link.target_component.node
            for component in node.components_model.list_components()
            for link in component.output_links
        ]

    def register_link(self, link: Link):
        """Register a link and attach it to both of its components.

        Args:
            link (Link): link to register. Invalid links are skipped.

        Raises:
            StageObjectRegistrationError: if the uuid is used by another object.
        """
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
        """Unregister a link and detach it from both of its components.

        Args:
            link (LinkLike): link, uuid or path.
        """
        link = self.get_object(link)
        source_cpnt: NodeComponent = self.get_object(link.source)
        target_cpnt: NodeComponent = self.get_object(link.target)
        source_cpnt.remove_link(link_uuid=link.uuid)
        target_cpnt.remove_link(link_uuid=link.uuid)
        # Last: views notified by remove_link may still look the link up.
        self._uuid_map.pop(link.uuid, None)

    def collect_links(self, from_node: NodeLike | None = None) -> list[Link]:
        """Collect links touching a node and its descendants.

        Args:
            from_node (NodeLike | None): node to start from. Defaults to the root node.

        Returns:
            list[Link]: collected links.
        """
        result = []
        from_node = self.get_object(from_node) if from_node else self.root_node
        serialized_node = from_node.serialize()
        for link_data in serialized_node[Node.LINKS_KEY]:
            result.append(self.get_object(link_data[StageObject.UUID_KEY]))
        return result

    def register_node(self, node: Node):
        """Register a node and its components in the uuid map.

        Args:
            node (Node): node to register.

        Raises:
            StageObjectRegistrationError: if a uuid is used by another object.
        """
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

        for util_object in node.util_objects:
            self.register_util_object(util_object)

    def register_util_object(self, util_object: UtilObject):
        """Register a util object in the uuid map.

        Args:
            util_object (UtilObject): object to register.

        Raises:
            StageObjectRegistrationError: if the uuid is used by another object.
        """
        if (
            util_object.uuid in self._uuid_map
            and self._uuid_map[util_object.uuid] is not util_object
        ):
            raise StageObjectRegistrationError(
                f"Util object with UUID {util_object.uuid} already exists: "
                f"{self._uuid_map[util_object.uuid]}"
            )
        self._uuid_map[util_object.uuid] = util_object

    def unregister_util_object(self, util_object: UtilObject):
        """Remove a util object from the uuid map.

        Args:
            util_object (UtilObject): object to unregister.
        """
        self._uuid_map.pop(util_object.uuid, None)

    def unregister_node(self, node: NodeLike):
        """Unregister a node, its components and its descendants.

        Args:
            node (NodeLike): node to unregister.

        Raises:
            StageObjectUnregistrationError: if the node is the root node.
        """
        if node is self.root_node:
            raise StageObjectUnregistrationError("Can't unregister root node")

        node: Node = self.get_object(node)
        self._uuid_map.pop(node.uuid, None)
        for util_object in node.util_objects:
            self._uuid_map.pop(util_object.uuid, None)
        descendant_nodes = node.list_children_tree()
        for component in node.components_model.list_components():
            self._uuid_map.pop(component.uuid, None)
            # Links left are the ones inside what is removed, like the internal
            # links of a reference node.
            for link_uuid in component.links_uuids:
                self._uuid_map.pop(link_uuid, None)

        for child_node in descendant_nodes:
            self.unregister_node(child_node)

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

    def delete_node(
        self, nodes: Sequence[NodeLike] | NodeLike, ignore_lock: bool = False
    ) -> None:
        """Delete node from stage.

        Args:
            nodes: nodes to delete.
            ignore_lock (bool): delete locked nodes too, for the node owning them.

        """
        if not isinstance(nodes, Sequence):
            nodes = [nodes]
        for node in nodes:
            node = self.get_object(node)
            if node is None:
                raise RuntimeError(f"{self} | Failed to delete node.")

            if node.is_locked and not ignore_lock:
                raise RuntimeError("Can't delete locked node: %s", node.path)

            # Removed uuids for node, childrent and components
            self.unregister_node(node)

            parent = node.parent()
            self.removeRow(node.row(), parent.index())
            self.node_deleted.emit(node.uuid)

    def on_node_changed(self, node: Node):
        """Forward item changes to the node.

        Args:
            node (Node): changed node.
        """
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

        # Set first: nodes loading from relative paths need the folder of the stage.
        self.file_path = pathlib.Path(file_path)
        Node.deserialize(serialized_node=json_data, node=self.root_node)
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
            command.validate_not_locked()

        for command in commands:
            self.undo_stack.push(command)

    def pathify(
        self, stage_object: StageObject | UUID | pathlib.PurePosixPath | str
    ) -> pathlib.PurePosixPath:
        """Convert a stage object, uuid or path-like value to a path.

        Args:
            stage_object (StageObject | UUID | pathlib.PurePosixPath | str): value to
                convert.

        Returns:
            pathlib.PurePosixPath: path of the object.
        """
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
