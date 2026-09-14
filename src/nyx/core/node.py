import enum
import logging
import pathlib
import time
import typing
from collections import OrderedDict, deque

from PySide6 import QtCore, QtGui

from .node_component.components_model import NodeComponentsModel
from .serializable import Serializable
from .plugin_subsystem.registry import NYX_REGISTRY
from ..utils import file_fn, inspect_fn
from ..static.vars import NYX_FILE_EXTENSION

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.editor.graphics.graphics_node import GraphicsNode
    from nyx.core.node_component._base_component import NodeComponent


LOGGER = logging.getLogger(__name__)


class Node(QtGui.QStandardItem, Serializable):
    TYPE_ID = ""
    CATEGORY = ""
    TRACK_NYX_VERSION = True

    class Roles(enum.IntEnum):
        ACTIVE_ROLE = QtCore.Qt.UserRole + 1
        POSITION = enum.auto()
        REFERENCE_FILE_PATH = enum.auto()
        LOCKED_ROLE = enum.auto()

    def __init__(
        self,
        name: str = "node",
        parent: Node | pathlib.PurePosixPath | str | None = None,
    ) -> None:
        QtGui.QStandardItem.__init__(self, name)
        Serializable.__init__(self)
        self._cached_path = None
        self.gr_node: GraphicsNode = None
        self._set_default_role_values()

        if parent:
            parent.appendRow(self)

        self._components_model = NodeComponentsModel(node=self)
        self.setup()

    def setup(self):
        pass

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)} ({self.cached_path})"

    def __hash__(self) -> int:
        return hash(self.path)

    def _set_default_role_values(self):
        self.setData(True, role=self.Roles.ACTIVE_ROLE)
        self.setData(QtCore.QPointF(), role=self.Roles.POSITION)
        self.setData(None, role=self.Roles.REFERENCE_FILE_PATH)
        self.setData(False, role=self.Roles.LOCKED_ROLE)

    @property
    def name(self):
        """Node name

        Returns:
            str: name.

        """
        return self.text()

    @property
    def is_stage_root_node(self):
        return self.cached_path == self.stage.ROOT_NODE_PATH

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
    def cached_path(self) -> pathlib.PurePosixPath:
        return self._cached_path

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
        return self.data(role=self.Roles.REFERENCE_FILE_PATH)

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

    def cache_current_path(self):
        """Store current path in cache."""
        self._cached_path = self.path

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
        return self.data(role=Node.Roles.POSITION)

    def serializable_position(self):
        position = self.position()
        return [position.x(), position.y()]

    def set_position(self, position: QtCore.QPointF):
        self.setData(position, role=Node.Roles.POSITION)

    def comment(self) -> str:
        return self.data(role=Node.Roles.COMMENT)

    def set_comment(self, text: str):
        self.setData(text, role=Node.Roles.COMMENT)

    def set_reference_file(self, path: pathlib.Path | str):
        self.setData(pathlib.Path(path), role=Node.Roles.REFERENCE_FILE_PATH)

    def appendRow(self, items: typing.Sequence[Node]) -> None:
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
            unique_name = self.stage.generate_unique_node_name(
                node.name, parent_node=self
            )
            new_path = self.path / unique_name
            if new_path in self.stage.path_map:
                LOGGER.error(f"Duplicate path: {new_path}")
                raise ValueError

            node.setText(unique_name)
            super().appendRow(node)
            assert node.path == new_path
            LOGGER.debug(f"{self} | added child node {new_path}")

            node.cache_current_path()
            self.stage._path_map[node.path] = node

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
        self._update_pathmap_entry()

    def _update_pathmap_entry(self):
        """Update path stored for in stage path map."""
        self.stage._path_map.pop(self.cached_path)
        self.stage._path_map[self.path] = self
        self.cache_current_path()
        for child_node in self.list_children():
            child_node._update_pathmap_entry()

    def child_names_set(self):
        """Get set of existing child names.

        Returns:
            set[str]: child names.

        """
        return {node.text() for node in self.list_children()}

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
        return [child_node.cached_path for child_node in self.list_children()]

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
            other_node = self.stage.path_resolver.computer_absolute_path(
                self.cached_path, other_node
            )

        other_node = self.stage.node(other_node)
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
        data = super().serialize()
        children = [child.serialize() for child in self.list_children()]
        data["name"] = self.text()
        data["type_id"] = self.TYPE_ID
        data["active"] = self.is_active()
        data["position"] = self.serializable_position()
        data["path"] = self.path.as_posix()
        data["required_plugins"] = self.REQUIRED_PLUGINS
        if self.reference_file_path is not None:
            data["reference_file_path"] = self.reference_file_path.as_posix()
        else:
            data["children"] = children
        data.update(self.components_model.serialize())
        return data

    def deserialize(self, data: OrderedDict):
        """Deserialize node from serialized node dictionary.

        Args:
            data (OrderedDict): Node data dictionary.

        """
        super().deserialize(data)

        if self.name != data.get("name", self.name):
            self.rename(data.get("name"))

        # Roles that should exist for normal and reference nodes
        self.set_active(data.get("active", True))
        self.set_position(QtCore.QPointF(*data.get("position", [0.0, 0.0])))

        # Get data from reference
        reference_file_path = data.get("reference_file_path")
        if reference_file_path:
            reference_file_path = pathlib.Path(reference_file_path)
            self.set_reference_file(reference_file_path)
            data = self._load_reference_file_data()

        self._update_pathmap_entry()

        # Children
        for child_data in data.get("children", {}):
            node_class = NYX_REGISTRY.get_node_cls(data.get("type_id")) or Node
            child_node = node_class(parent=self)
            child_node.deserialize(child_data)

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

    def find_child_node_of_type(self, type_id: str):
        for node in self.list_children():
            if node.TYPE_ID == type_id:
                return node

    def build_execution_queue(self) -> deque[pathlib.PurePosixPath]:
        """Build execution queue from given node.

        Returns:
            deque[pathlib.PurePosixPath]: Execution queue.

        """
        # TODO: Reimplement by quering flow components
        exec_queue = deque()
        if self.is_active():
            return exec_queue
        return exec_queue

    def execute(self):
        """Execute this node.

        Raises:
            err: run time exception raised during code execution.

        """
        if not self.is_active():
            return

        start_time = time.perf_counter()
        try:
            LOGGER.info(f"TODO: Executing {self.cached_path}")
            # TODO: Execute components
        except Exception as err:
            LOGGER.exception(f"{self} | Execution error.")
            raise err

        total_time = time.perf_counter() - start_time
        LOGGER.info(f"Executed in {total_time:.4f}: {self.cached_path}")
