import enum
import logging
import pathlib
import time
import typing
from collections import OrderedDict, deque
from collections.abc import Iterable

from uuid import UUID
from PySide6 import QtCore, QtGui

from .stage_object import StageObject
from .models.components_model import NodeComponentsModel
from .plugin_subsystem.registry import NYX_REGISTRY
from ..utils import file_fn, inspect_fn
from ..static.vars import NYX_FILE_EXTENSION
from ..static.enums import CoreNodes, RestoreUuidOption, NodeExecutionStatus

if typing.TYPE_CHECKING:
    from .stage import Stage
    from .node_component import NodeComponent
    from .stage_crawler import NodeVisitor
    from nyx.editor.graphics.graphics_node import GraphicsNode
    from nyx.plugins.core.nodes.flow_start import FlowStartNode


LOGGER = logging.getLogger(__name__)

type NodeLike = Node | UUID | pathlib.PurePosixPath | str


class Node(QtGui.QStandardItem, StageObject):
    DEFAULT_NAME = "node"
    TRACK_NYX_VERSION: bool = True

    TYPE_ID_KEY = "type_id"
    NAME_KEY = "name"
    ACTIVE_KEY = "active"
    POSITION_KEY = "position"
    REFERENCE_FILE_KEY = "reference_file_path"
    COMPONENTS_KEY = "components"
    CHILDREN_KEY = "children"

    class Roles(enum.IntEnum):
        TYPE_ID_ROLE = QtCore.Qt.UserRole + 1
        TYPE_DISPLAY_NAME_ROLE = enum.auto()
        ACTIVE_ROLE = enum.auto()
        POSITION_ROLE = enum.auto()
        REFERENCE_FILE_PATH_ROLE = enum.auto()
        TAGS_ROLE = enum.auto()
        LOCKED_ROLE = enum.auto()
        EXECUTION_STATUS_ROLE = enum.auto()
        RAISED_EXCEPTION_ROLE = enum.auto()

    def __init__(
        self,
        name: str | None = None,
        uuid: UUID | str | None = None,
        parent: Node | None = None,
    ) -> None:
        QtGui.QStandardItem.__init__(self, name or self.DEFAULT_NAME)
        StageObject.__init__(self, uuid=uuid)
        self._set_default_role_values()
        self._components_model = NodeComponentsModel(node=self)
        self.gr_node: GraphicsNode = None

        if parent:
            parent.appendRow(self)

    def setup(self):
        pass

    def post_setup_hook(self):
        self._mark_setup_components_as_builtin()

    def _mark_setup_components_as_builtin(self):
        for component in self.components_model.list_components():
            component.mark_as_built_in()

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)} ({self.path})"

    def __hash__(self) -> int:
        return hash(self.path)

    def __getitem__(self, key: str):
        return self.components_model.get_component(key)

    def _set_default_role_values(self):
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID_ROLE)
        self.setData(True, role=self.Roles.ACTIVE_ROLE)
        self.setData(QtCore.QPointF(), role=self.Roles.POSITION_ROLE)
        self.setData(None, role=self.Roles.REFERENCE_FILE_PATH_ROLE)
        self.setData(False, role=self.Roles.LOCKED_ROLE)
        self.setData(self.get_tags(), role=self.Roles.TAGS_ROLE)
        self.setData(
            self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME_ROLE
        )
        self.setData(None, role=self.Roles.RAISED_EXCEPTION_ROLE)
        self.setData(NodeExecutionStatus.NOT_RAN, role=self.Roles.EXECUTION_STATUS_ROLE)

    @property
    def name(self):
        """Node name

        Returns:
            str: name.

        """
        return self.text()

    @property
    def is_stage_root_node(self):
        return self is self.stage.root_node

    @property
    def scope(self):
        return tuple(self.path.parents)[0]

    @property
    def path(self) -> pathlib.PurePosixPath:
        """Get current node path.

        Returns:
            pathlib.PurePosixPath: absolute node path.

        """
        path = pathlib.PurePosixPath("/")
        if not self.parent():
            return path / self.name
        return self.parent().path / self.name

    @property
    def stage(self) -> Stage:
        """Utility method pointing to node's stage (model).

        Returns:
            Stage: stage node belongs to.

        """
        return self.model()

    @property
    def components_model(self) -> NodeComponentsModel:
        """Get components model.

        Returns:
            NodeComponentsModel: components model
        """
        return self._components_model

    @property
    def reference_file_path(self) -> pathlib.Path | None:
        return self.data(role=self.Roles.REFERENCE_FILE_PATH_ROLE)

    @property
    def is_referenced(self):
        nodes = [self]
        nodes.extend(self.list_parents())
        return any([node.reference_file_path is not None for node in nodes])

    @property
    def is_locked(self):
        return self.data(self.Roles.LOCKED_ROLE)

    @is_locked.setter
    def is_locked(self, state: bool):
        self.setData(state, self.Roles.LOCKED_ROLE)

    @property
    def tags(self) -> set[str]:
        return self.data(role=self.Roles.TAGS_ROLE)

    @tags.setter
    def tags(self, new_tags: Iterable) -> None:
        self.setData(set(new_tags), role=self.Roles.TAGS_ROLE)

    @property
    def raised_exception(self) -> Exception | None:
        return self.data(self.Roles.RAISED_EXCEPTION_ROLE)

    @raised_exception.setter
    def raised_exception(self, err: Exception) -> None:
        return self.setData(err, self.Roles.RAISED_EXCEPTION_ROLE)

    @property
    def execution_status(self) -> NodeExecutionStatus:
        return self.data(self.Roles.EXECUTION_STATUS_ROLE)

    @execution_status.setter
    def execution_status(self, status: NodeExecutionStatus) -> None:
        self.setData(status, role=self.Roles.EXECUTION_STATUS_ROLE)

    def reset_execution_status(self):
        self.execution_status = NodeExecutionStatus.NOT_RAN

    def is_active(self) -> bool:
        """Query if node's active state.

        Returns:
            bool: current active state.

        """
        return self.data(role=Node.Roles.ACTIVE_ROLE)

    def set_active(self, state: bool):
        """Set active state.

        Args:
            state (bool): new active state.

        """
        self.setData(state, role=Node.Roles.ACTIVE_ROLE)

    def deactivate(self):
        """Set node's active state to False."""
        self.set_active(False)

    def activate(self):
        """Set node's active state to True."""
        self.set_active(True)

    def position(self) -> QtCore.QPointF:
        return self.data(role=Node.Roles.POSITION_ROLE)

    def serializable_position(self):
        position = self.position()
        return [position.x(), position.y()]

    def set_position(self, position: QtCore.QPointF):
        self.setData(position, role=Node.Roles.POSITION_ROLE)

    def set_reference_file(self, path: pathlib.Path | str):
        self.setData(pathlib.Path(path), role=Node.Roles.REFERENCE_FILE_PATH_ROLE)

    def appendRow(self, items: Node | typing.Sequence[Node]) -> None:
        """Override Qt method.

        - Generates new unique name.
        - Set cached path to current.
        - Store path into stage path map.

        Args:
            items (typing.Sequence): items to append.

        Raises:
            ValueError: path exists in stage path map.

        """
        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            if node.uuid in self.stage.uuid_map:
                raise KeyError(
                    f"Node with UUID {node.uuid} already exists: "
                    f"{(self.stage.get_object(node.uuid).path)}"
                )

            unique_name = self.stage.generate_unique_node_name(
                node.name, parent_node=self
            )

            node.setText(unique_name)
            super().appendRow(node)

            self.stage.uuid_map[node.uuid] = node
            node.setup()
            node.post_setup_hook()

    def rename(self, new_name: str):
        """Rename node.

        - Also update path for self and children in path map.

        Args:
            new_name (str): new node name.

        """
        if new_name == self.name:
            return

        new_name = self.stage.generate_unique_node_name(
            new_name, parent_node=self.parent()
        )
        self.setText(new_name)

    @property
    def child_names_set(self) -> set[str]:
        """Get set of existing child names.

        Returns:
            set[str]: child names.

        """
        return {node.name for node in self.list_children()}

    def list_children(self) -> list[Node]:
        """List child nodes.

        Returns:
            list[Node]: child nodes.

        """
        children = [self.child(row) for row in range(self.rowCount())]
        return children

    def list_children_paths(self) -> list[pathlib.PurePosixPath]:
        """List of child paths.

        Returns:
            list[pathlib.PurePosixPath]: child paths.

        """
        return [child_node.path for child_node in self.list_children()]

    def list_children_tree(self) -> list[Node]:
        """List children tree recursively.

        Returns:
            list[Node]: child nodes tree.

        """
        children = self.list_children()
        for child in children:
            children += child.list_children()
        return children

    def is_parent_of(self, other_node: Node | str | pathlib.PurePosixPath):
        """Check if given path is path of one of the child nodes.

        Args:
            path (str | pathlib.PurePosixPath): path to test.

        Returns:
            bool: if path belongs to one of children.

        """
        if isinstance(
            other_node, (str, pathlib.PurePosixPath)
        ) and self.stage.path_resolver.is_relative_path(other_node):
            other_node = self.stage.path_resolver.compute_absolute_path(
                self.path, other_node
            )

        other_node = self.stage.get_object(other_node)
        return other_node in set(self.list_children())

    def list_parents(self, as_queue=False) -> list[Node] | deque[Node]:
        """List parents recursively.

        Args:
            as_queue: If result should be returned as deque. Defaults to False.

        Returns:
            list[Node] | deque[Node]: parent nodes collection.

        """
        parents = deque()
        direct_parent: Node = self.parent()
        if direct_parent and not direct_parent.is_stage_root_node:
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        """Delete this node from stage."""
        self.stage.delete_node(self)

    def add_component(self, node_component: NodeComponent):
        self.components_model.add_component(node_component)

    def on_changed(self):
        pass

    def serialize(self) -> OrderedDict:
        """Serialize node to dict.

        Returns:
            OrderedDict: serialized data

        """
        serialized_data = super().serialize()
        serialized_data["name"] = self.name
        serialized_data["type_id"] = self.get_type_id()
        serialized_data["active"] = self.is_active()
        serialized_data["position"] = self.serializable_position()
        serialized_data.update(self.components_model.serialize())
        if self.reference_file_path is not None:
            serialized_data[self.REFERENCE_FILE_KEY] = (
                self.reference_file_path.as_posix()
            )
        else:
            serialized_data[self.CHILDREN_KEY] = [
                child_node.serialize() for child_node in self.list_children()
            ]
        return serialized_data

    @classmethod
    def deserialize(
        cls,
        serialized_node: OrderedDict[str, typing.Any],
        node: Node | None = None,
        parent_node: Node | None = None,
        restore_uuid: RestoreUuidOption = RestoreUuidOption.ATTEMPT_RESTORE,
    ) -> Node:
        stage = parent_node.stage if parent_node is not None else None
        uuid = cls.choose_new_uuid(
            stage=stage,
            serialized_data=serialized_node,
            restore_option=restore_uuid,
        )

        if not node:
            node_cls = NYX_REGISTRY.get_node_cls(serialized_node[cls.TYPE_ID_KEY])
            node = node_cls(
                name=serialized_node[cls.NAME_KEY], uuid=uuid, parent=parent_node
            )
        else:
            node.rename(serialized_node[cls.NAME_KEY])

        LOGGER.debug(f"Deserializing: {serialized_node.get(cls.NAME_KEY)}")
        if uuid is not None:
            node.uuid = uuid

        # Roles that should exist for normal and reference nodes
        node.set_active(serialized_node.get(cls.ACTIVE_KEY, True))
        node.set_position(
            QtCore.QPointF(*serialized_node.get(cls.POSITION_KEY, [0.0, 0.0]))
        )

        # Get data from reference
        reference_file_path = serialized_node.get(cls.REFERENCE_FILE_KEY)
        if reference_file_path:
            reference_file_path = pathlib.Path(reference_file_path)
            node.set_reference_file(reference_file_path)
            serialized_node = node._load_reference_file_data()

        # Components
        node.components_model.deserialize(serialized_node.get(cls.COMPONENTS_KEY))

        # Children
        for child_data in serialized_node.get(cls.CHILDREN_KEY, {}):
            cls.deserialize(
                serialized_node=child_data,
                parent_node=node,
                restore_uuid=restore_uuid,
            )

        return node

    def _load_reference_file_data(self) -> OrderedDict:
        data = OrderedDict()
        try:
            if self.reference_file_path.suffix == NYX_FILE_EXTENSION:
                data = file_fn.load_json(
                    self.reference_file_path, object_pairs_hook=OrderedDict
                )
            else:
                raise ValueError(f"Invalid file type: {self.reference_file_path}")
        except FileNotFoundError:
            LOGGER.exception(f"Reference file doesn't exist: {self.reference_file_path}")
        return data

    def export_to_json(self, file_path: pathlib.Path):
        """Export node to json file.

        Args:
            file_path (pathlib.Path): json file path.

        """
        data = self.serialize()
        file_fn.write_json(file_path, data)

    def load_from_json(self, file_path: pathlib.Path):
        """Load node from json file.

        Args:
            file_path (pathlib.Path): json file path.
            as_reference (bool, optional): if node should be locked. Defaults to False.

        """
        json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        self.deserialize(json_data)

    def find_child_by_name(self, name) -> Node | None:
        for node in self.list_children():
            if node.name == name:
                return node

    def find_child_node_of_type(self, type_id: str) -> Node | None:
        for node in self.list_children():
            if node.get_type_id() == type_id:
                return node

    def find_flow_start_node(self) -> FlowStartNode:
        """Find first child flow start node

        Returns:
            FlowStartNode instance.
        """
        return self.find_child_node_of_type(type_id=CoreNodes.FLOW_START)

    def accept_visitor(self, visitor: NodeVisitor):
        if not self.is_active():
            LOGGER.warning("Not Active: %s", self.path.as_posix())
            return
        visitor.visit_node(self)

    def pre_execution(self):
        self.setData(None, self.Roles.RAISED_EXCEPTION_ROLE)

    def pre_execution_hook(self):
        pass

    def post_execution_hook(self):
        pass

    def evaluate(self):
        """Evaluate components values on this node.

        Raises:
            err: run time exception raised during code execution.

        """
        pass

    def execute(self):
        pass

    def evaluate_components(self):
        for component in self.components_model.list_components():
            component.evaluate()

    def execute_components(self):
        for component in self.components_model.list_components():
            component.execution_hook()

    def execution_hook(self):
        """Execute this node.

        Raises:
            err: run time exception raised during code execution.

        """
        self.reset_execution_status()
        if not self.is_active():
            return

        self.execution_status = NodeExecutionStatus.PENDING
        start_time = time.perf_counter()
        try:
            self.pre_execution_hook()
            self.evaluate_components()
            self.evaluate()
            self.execute_components()
            self.execute()
            self.post_execution_hook()
        except Exception as err:
            LOGGER.exception(f"{self} | Execution error.")
            self.raised_exception = err
            self.execution_status = NodeExecutionStatus.ERROR
            raise err
        else:
            self.execution_status = NodeExecutionStatus.SUCCESS

        total_time = time.perf_counter() - start_time
        LOGGER.info(f"Executed in {total_time:.4f}: {self.path}")

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.EMPTY

    @classmethod
    def get_type_display_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_tags(cls) -> set[str]:
        return set()
