import enum
import logging
import pathlib
import time
import typing
from collections import OrderedDict, deque

from PySide6 import QtCore, QtGui

from nyx.core import constants
from nyx.core.node_component.components_model import NodeComponentsModel
from nyx.core.serializable import Serializable
from nyx.utils import file_fn, inspect_fn
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.editor.graphics.graphics_node import GraphicsNode
    from nyx.core.node_component._base_component import NodeComponent


LOGGER = logging.getLogger(__name__)


class Node(QtGui.QStandardItem, Serializable):
    TYPE_ID = ""
    CATEGORY = ""
    METADATA = {"type": "node"}
    TRACK_NYX_VERSION = True

    class Roles(enum.IntEnum):
        INPUT_EXEC = QtCore.Qt.UserRole + 1
        OUTPUT_EXEC = enum.auto()
        ACTIVE_ROLE = enum.auto()
        EXECUTION_START_PATH = enum.auto()
        POSITION = enum.auto()
        COMMENT = enum.auto()
        REFERENCE_FILE_PATH = enum.auto()

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
        self.setData(None, role=Node.Roles.INPUT_EXEC)
        self.setData(None, role=Node.Roles.OUTPUT_EXEC)
        self.setData(True, role=Node.Roles.ACTIVE_ROLE)
        self.setData(None, role=Node.Roles.EXECUTION_START_PATH)
        self.setData(QtCore.QPointF(), role=Node.Roles.POSITION)
        self.setData("", role=Node.Roles.COMMENT)
        self.setData(None, role=Node.Roles.REFERENCE_FILE_PATH)

    @property
    def name(self):
        """Node name

        Returns:
            str: name.

        """
        return self.text()

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
    def cached_path(self):
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
            as_queue (bool, optional): if result should be returned as deque. Defaults to False.

        Returns:
            list[Node] | deque[Node]: parent nodes collection.

        """
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        """Delete this node from stage."""
        self.stage.delete_node(self)

    def get_input_exec_path(
        self, serializable=False
    ) -> pathlib.PurePosixPath | str | None:
        """Get path for the node that is set as execution dependency.

        Args:
            serializable (bool, optional): Return value is serializable. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: Execution dependency node path.

        """
        path: pathlib.PurePosixPath = self.data(role=Node.Roles.INPUT_EXEC)
        if path is None or not serializable:
            return path
        return path.as_posix()

    def get_output_exec_path(
        self, serializable=False
    ) -> pathlib.PurePosixPath | str | None:
        """Get path for the node that is execution dependee of this node.

        Args:
            serializable (bool, optional): Return value is serializable. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: Execution dependee node path.

        """
        path: pathlib.PurePosixPath = self.data(role=Node.Roles.OUTPUT_EXEC)
        if path is None or not serializable:
            return path
        return path.as_posix()

    def is_input_exec_cyclic(
        self, other_node: Node | pathlib.PurePosixPath | str
    ) -> bool:
        other_node = self.stage.node(other_node)
        return other_node.get_input_exec_path() == self.path

    def set_input_exec_path(
        self, path: pathlib.PurePosixPath | str | Node, silent=False
    ) -> None:
        """Set given node as execution dependency.

        Args:
            path (pathlib.PurePosixPath | str | Node): Node instance or path.
            silent (bool, optional): Do not notify other nodes of the change,
            and just set data. Defaults to False.

        Raises:
            TypeError: Invalid input provided.

        """
        if isinstance(path, Node):
            path = path.path
        elif isinstance(path, pathlib.PurePosixPath):
            pass
        elif isinstance(path, str):
            path = pathlib.PurePosixPath(path)
        elif path is None:
            pass
        else:
            LOGGER.error(f"{self} | Invalid input exec path: {path}")
            raise TypeError("Invalid input exec path type")

        if silent:
            self.setData(path, role=Node.Roles.INPUT_EXEC)
            return

        new_input_exec_node: Node = self.stage.node(path)
        previous_input_exec_node = self.stage.node(self.get_input_exec_path())
        if new_input_exec_node == previous_input_exec_node:
            LOGGER.debug(f"{self} | exec output set to {path}")
            return

        if new_input_exec_node and new_input_exec_node.scope != self.scope:
            LOGGER.error(
                f"{self} | Invalid new input scope: {new_input_exec_node.scope}"
            )
            return

        # Set connections
        if new_input_exec_node is None:
            self.setData(None, role=Node.Roles.INPUT_EXEC)
        else:
            self.setData(new_input_exec_node.path, role=Node.Roles.INPUT_EXEC)

        # Reset old input node
        if previous_input_exec_node is not None:
            previous_input_exec_node.set_output_exec_path(None, silent=True)

        # Get path from new node to self
        # If its different from self.path -> store new path
        if new_input_exec_node is not None:
            if new_input_exec_node.get_output_exec_path() != self.path:
                new_input_exec_node.set_output_exec_path(self.path)

    def set_output_exec_path(
        self, path: pathlib.PurePosixPath | str | Node, silent=False
    ) -> None:
        """Set given node as execution dependee.

        Args:
            path (pathlib.PurePosixPath | str | Node): Dependee node instance or path.
            silent (bool, optional): Do not notify other nodes of the change,
            and just set data. Defaults to False.

        Raises:
            TypeError: Invalid input provided.

        """
        if isinstance(path, Node):
            path = path.path
        elif isinstance(path, pathlib.PurePosixPath):
            pass
        elif isinstance(path, str):
            path = pathlib.PurePosixPath(path)
        elif path is None:
            pass
        else:
            LOGGER.error(f"{self} | Invalid output exec path: {path}")
            raise TypeError("Invalid output exec path type")

        if silent:
            self.setData(path, role=Node.Roles.OUTPUT_EXEC)
            return

        new_output_exec_node = self.stage.node(path)
        previous_output_exec_node = self.stage.node(self.get_output_exec_path())
        if new_output_exec_node == previous_output_exec_node:
            LOGGER.debug(f"{self} | exec output set to {path}")
            return

        if new_output_exec_node and new_output_exec_node.scope != self.scope:
            LOGGER.error(
                f"{self} | Invalid new output scope: {new_output_exec_node.scope}"
            )
            return
        # Set connections
        if new_output_exec_node is None:
            self.setData(None, role=Node.Roles.OUTPUT_EXEC)
        else:
            self.setData(new_output_exec_node.path, role=Node.Roles.OUTPUT_EXEC)

        # Reset old output node
        if previous_output_exec_node is not None:
            previous_output_exec_node.set_input_exec_path(None, silent=True)

        # Get path from new node to self
        # If its different from self.path -> store new path
        if new_output_exec_node is not None:
            if new_output_exec_node.get_output_exec_path() != self.path:
                new_output_exec_node.set_input_exec_path(self.path)

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
        data["input_exec"] = self.get_input_exec_path(serializable=True)
        data["output_exec"] = self.get_output_exec_path(serializable=True)
        data["required_plugins"] = self.REQUIRED_PLUGINS
        if self.reference_file_path is not None:
            data["reference_file_path"] = self.reference_file_path.as_posix()
        else:
            data["execution_start_path"] = self.get_execution_start_path(
                serializable=True
            )
            data["children"] = children
            data["comment"] = self.comment()
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
        self.set_input_exec_path(data.get("input_exec", ""), silent=True)
        self.set_output_exec_path(data.get("output_exec", ""), silent=True)
        self.set_position(QtCore.QPointF(*data.get("position", [0.0, 0.0])))

        # Get data from reference
        reference_file_path = data.get("reference_file_path")
        if reference_file_path:
            reference_file_path = pathlib.Path(reference_file_path)
            self.set_reference_file(reference_file_path)
            data = self._load_reference_file_data()

        self.set_execution_start_path(data.get("execution_start_path"))
        self.set_comment(data.get("comment", ""))

        self._update_pathmap_entry()

        # Children
        for child_data in data.get("children", {}):
            node_class = NYX_REGISTRY.get_node_cls(data.get("type_id")) or Node
            child_node = node_class(parent=self)
            child_node.deserialize(child_data)

    def _load_reference_file_data(self) -> OrderedDict:
        data = OrderedDict()
        try:
            if self.reference_file_path.suffix == constants.NYX_FILE_EXTENSION:
                data = file_fn.load_json(
                    self.reference_file_path, object_pairs_hook=OrderedDict
                )
                if data["metadata"]["type"] == "stage":
                    data = self.stage.convert_stage_to_node(
                        stage=data, name=self.reference_file_path.stem
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

    def set_execution_start_path(self, child_path: pathlib.PurePosixPath | str | None):
        """Set execution start path to one of the child node's path.

        Args:
            child_path (pathlib.PurePosixPath | None): execution start node path.

        """
        if isinstance(child_path, Node):
            child_path = child_path.cached_path

        elif isinstance(child_path, str):
            child_path = pathlib.PurePosixPath(child_path)

        self.setData(child_path, role=Node.Roles.EXECUTION_START_PATH)
        LOGGER.info(f"{self} | Set execution start path to: {child_path}")

    def get_execution_start_path(
        self, serializable=False
    ) -> pathlib.PurePosixPath | str | None:
        """Get execution start path. Can be child path or None.

        Args:
            serializable (bool, optional): get path as jsonable str or None. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: execution start path

        """
        path = self.data(role=Node.Roles.EXECUTION_START_PATH)
        if serializable and isinstance(path, pathlib.PurePosixPath):
            path = path.as_posix()
        return path

    def build_execution_queue(self) -> deque[pathlib.PurePosixPath]:
        """Build execution queue from given node.

        Returns:
            deque[pathlib.PurePosixPath]: Execution queue.

        """
        exec_queue = deque()
        if self.is_active():
            exec_queue.append(self.cached_path)
            child_path = self.get_execution_start_path()
            if child_path:
                # TODO: check if relative and convert to abs
                if self.stage.path_resolver.is_relative_path(child_path):
                    child_path = self.stage.path_resolver.computer_absolute_path(
                        self.cached_path, child_path
                    )
                child_node = self.stage.node(child_path)
                if child_node:
                    exec_queue.extend(child_node.build_execution_queue())
                else:
                    LOGGER.warning(f"{self} | start path doesn't exist: {child_path}")

        output_path = self.get_output_exec_path()
        if output_path:
            output_node = self.stage.node(output_path)
            if output_node:
                exec_queue.extend(output_node.build_execution_queue())
            else:
                LOGGER.warning(
                    f"{self} | output exec path doesn't exist: {output_path} "
                )

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
